import json
import requests
import boto3
import os
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)
pipelineClient = boto3.client('codepipeline')
ssmClient = boto3.client('ssm')
FAILED = 'FAILED'
SUCCEEDED = 'SUCCEEDED'
STARTED = 'STARTED'


# lambda handler for github webhooks
def lambda_handler(event, context):
    log_info({"EVENT:": event})
    message = "success"
    status = 200

    if is_github_event(event):
        action = get_github_action(event)
        if action == 'opened' or action == 'synchronize':
            try:
                create_or_start_pipeline(event)
            except Exception as e:
                message = str(e)
                status = 500
        elif action == 'closed':
            try:
                status = 200
                message = delete_pipeline(event)
            except Exception as e:
                message = str(e)
    else:
        log_info({'not a github event': event})

    return {
        "statusCode": status,
        "body": message
    }


# cloudwatch handler which receives events about pipeline
def cloudwatch_handler(event, context):
    log_info({"Action": "github_handler", "EVENT: ": event})
    pipeline_name = event['detail']['pipeline']
    pipeline_template_name = pipeline_name.split('_')[0]
    token = get_github_token(pipeline_template_name)
    github_status_urls = get_github_status_url(pipeline_template_name)

    if event['detail-type'] == 'CodePipeline Pipeline Execution State Change':
        notify_github_pipeline_execution_state_changes(event, token, github_status_urls, pipeline_name,
                                                       get_aws_region())

    if event['detail-type'] == 'CodePipeline Action Execution State Change':
        notify_github_pipeline_action_state_changes(event, token, github_status_urls)

    # needs more work here
    return {
        "statusCode": 200,
        "body": "success"
    }


# create or start the pipeline
def create_or_start_pipeline(event):
    new_pipeline_name = get_new_pipeline_name(event)
    log_info({"New Pipeline Name": new_pipeline_name})
    update_github_status_to_start(event, new_pipeline_name, get_aws_region())
    create_github_commit_hashes_in_ssm(event, get_pipeline_name())
    try:
        log_info("Starting Pipeline")
        start_pipeline(new_pipeline_name)
        # if pipeline is not found, this means we need to create one
    except Exception as e:
        log_info("trying to create a pipeline")
        try:
            create_pipeline(event)
        except Exception as e:
            log_critical("could not create a pipeline: " + str(e))
            raise Exception("could not created a pipeline: " + str(e))

    return True


# update the github status to start
def update_github_status_to_start(event, pipeline_name, region):
    log_debug("updating github status to start")
    message = json.loads(event['body'])
    token = get_github_token(get_pipeline_name())
    head = {"Authorization": "Bearer " + token}
    params = get_github_payload("STARTED", pipeline_name, region)
    log_info({"GITHUB_STATUSES_URL": message['pull_request']['statuses_url'], "PARAMS": params})
    requests.post(message['pull_request']['statuses_url'], json=params, headers=head)


# if a pipeline has stopped and a commit is pushed,
# we want to restart it.
def start_pipeline(new_pipeline_name):
    try:
        pipelineClient.start_pipeline_execution(name=new_pipeline_name)
        log_info("pipeline started: " + new_pipeline_name)
    except pipelineClient.exceptions.PipelineNotFoundException as e:
        log_error("pipeline not found: " + new_pipeline_name)
        raise Exception("PipelineNotFoundException: " + str(e))


# this clones the template and creates a new one
def create_pipeline(event):
    try:
        pipelineClient.get_pipeline(name=get_pipeline_name())
        clone_pipeline(event)
    except pipelineClient.exceptions.PipelineNotFoundException as e:
        log_critical("Pipeline cannot be created: " + get_pipeline_name())
        raise Exception("PipelineNotFoundException: " + str(e))


# delete pipeline and ssm parameters
def delete_pipeline(event):
    new_pipeline_name = get_new_pipeline_name(event)

    try:
        delete_ssm(new_pipeline_name)
        pipelineClient.delete_pipeline(name=new_pipeline_name)
        return new_pipeline_name
    except Exception as e:
        raise Exception(str(e))


# delete ssm parameters
def delete_ssm(pipeline_name):
    number = pipeline_name.split('-')[1]
    path = '/codepipeline/' + get_pipeline_name() + '/status_url/' + number
    try:
        result = ssmClient.delete_parameter(Name=path)
        if result['ResponseMetadata']['HTTPStatusCode'] == 200:
            return True
    except ssmClient.exceptions.ParameterNotFound as e:
        error_message = "Could not delete: " + path
        log_critical({"SSM": error_message, "Exception": e})
        raise Exception("SSM: " + error_message + " : " + str(e))


# create github commit hashes in ssm
def create_github_commit_hashes_in_ssm(event, pipeline):
    message = json.loads(event['body'])
    name = '/codepipeline/' + pipeline + '/status_url/' + str(message['number'])
    ssmClient.put_parameter(Name=name, Value=message['pull_request']['statuses_url'], Type='String', Overwrite=True)


# gets the github status url
def get_github_status_url(pipelinename):
    path = '/codepipeline/' + pipelinename + '/status_url'
    log_info("SSM_get_github_status_url_Path: " + path)
    result = ssmClient.get_parameters_by_path(Path=path)
    github_status_urls = {}
    for r in result['Parameters']:
        key = r['Name'].split('/')
        key = int(key[-1])
        github_status_urls[key] = r['Value']

    sorted_github_status_urls = sorted(github_status_urls)
    return github_status_urls[sorted_github_status_urls[-1]]


# check whether it is a github event or not
def is_github_event(event):
    if 'headers' not in event:
        print('No headers found')
        log_error({"event": {"no headers found": event}})
        return False

    headers = event['headers']
    if 'X-GitHub-Event' in headers:
        return True

    return False


# clones the pipeline from the template
def clone_pipeline(event):
    log_info("cloning pipeline")
    message = json.loads(event['body'])
    pr_branch = message['pull_request']['head']['ref']
    response = pipelineClient.get_pipeline(name=get_pipeline_name())
    response['pipeline']['name'] = get_new_pipeline_name(event)
    response['pipeline']['stages'][0]['actions'][0]['configuration']['OAuthToken'] = get_github_token(
        get_pipeline_name())
    response['pipeline']['stages'][0]['actions'][0]['configuration']['Branch'] = pr_branch

    try:
        result = pipelineClient.create_pipeline(
            pipeline=response['pipeline']
        )
        log_info({"Pipeline": {"create_pipeline": result}})
        return True
    except:
        log_critical("Pipeline couldn't be created")
        return False


# gets the name of the new pipeline
def get_new_pipeline_name(event):
    message = json.loads(event['body'])
    pr_number = message['pull_request']['number']
    repo_name = message['pull_request']['head']['repo']['name']
    return get_pipeline_name() + '_PR-' + str(pr_number) + '-Repo-' + repo_name


def get_github_token(pipelinename):
    log_info({"Pipeline Name": pipelinename, "Action": "get_github_token"})
    name = '/codepipeline/' + pipelinename + '/' + 'github_token'
    log_info("SSM_github_token: " + name)
    parameter = ssmClient.get_parameter(Name=name, WithDecryption=True)
    return parameter["Parameter"]["Value"]


def get_pipeline_name():
    name = "PIPELINE_NAME"
    pipeline_name = os.getenv(name, "")
    if not pipeline_name:
        log_critical("missing environment variable: " + name)
        raise Exception("environment variable: PIPELINE_NAME is missing ")

    return pipeline_name


# notify github about the build status
def notify_github_pipeline_execution_state_changes(event, token, github_endpoint, pipeline_name, region):
    head = {"Authorization": "Bearer " + token}
    status = get_status(event)
    params = get_github_payload(status, pipeline_name, region)
    notify_github_status_on_all_action_failures(pipeline_name, github_endpoint, head)
    r = requests.post(github_endpoint, json=params, headers=head)
    log_info({"Action": "notify_github", "CodePipeline Status: ": status, "Github Payload": params,
              "Github Endpoint": github_endpoint,
              "Github Response": r.content})


def notify_github_status_on_all_action_failures(pipeline_name, github_endpoint, head):
    pipeline_states = pipelineClient.get_pipeline_state(name=pipeline_name)
    for pi in pipeline_states['stageStates']:
        if pi['latestExecution']['status'] == 'Failed':
            context = "codepipeline/" + pi['stageName']
            log_info({"pipeline_states": context})
            params = {
                "state": 'failure',
                "context": context
            }
            r = requests.post(github_endpoint, json=params, headers=head)


def notify_github_pipeline_action_state_changes(event, token, github_endpoint):
    head = {"Authorization": "Bearer " + token}
    status = get_status(event)
    stage = event['detail']['stage']
    context = "codepipeline/" + stage
    github_status = get_github_status(status)
    params = {
        "state": github_status[0],
        "context": context
    }
    r = requests.post(github_endpoint, json=params, headers=head)
    log_info({"Action": "notify_action_github", "Context": context, "Github Payload": params,
              "Github Endpoint": github_endpoint, "Github response": r})


def get_codepipeline_console_url(pipeline_name, region):
    return "https://" + region + ".console.aws.amazon.com/codesuite/codepipeline/pipelines/" + pipeline_name + \
           "/view?region=" + region


def get_status(detail):
    return detail['detail']['state']


def get_github_payload(pipeline_status, pipeline_name, region):
    github_params = get_github_status(pipeline_status)

    return {
        "state": github_params[0],
        "description": github_params[1],
        "context": "CodePipeline",
        "target_url": get_codepipeline_console_url(pipeline_name, region)
    }


# maps codepipeline status to Github status
def get_github_status(pipeline_status):
    if pipeline_status == STARTED:
        return ['pending', 'Build started']

    if pipeline_status == SUCCEEDED:
        return ['success', 'Build Success']

    if pipeline_status == FAILED:
        return ['failure', 'Build Failed']


def get_github_action(event):
    body = json.loads(event['body'])
    if 'action' not in body:
        log_info('Missing Action in Github Payload')
        return ''

    log_info({"GITHUB": {"Action": body['action']}})
    return body['action']


def log_info(message):
    logger.setLevel(logging.INFO)
    logger.info(message)


def log_critical(message):
    logger.setLevel(logging.CRITICAL)
    logger.critical(message)


def log_error(message):
    logger.setLevel(logging.ERROR)
    logger.error(message)


def log_debug(message):
    logger.setLevel(logging.DEBUG)
    logger.debug(message)


def get_aws_region():
    return os.environ["region"]
