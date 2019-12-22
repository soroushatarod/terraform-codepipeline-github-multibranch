# TerraPy
<h2>Github AWS CodePipeline Multiple Branches - Terraform & Python <3 </h2>

<h3>Allows you to have multiple branches in codepipeline from Github with status update to each PR.</h3>

<h4>How does it works?</h4>
<ul>
  <li>When a developer submits a PR.</li>
<li>TerraPy clones a pipeline from the template.</li>
<li>On each stage it sends a status update to the PR.</li>
</ul>

<h4>In the example below, on each Pull Request created, a pipeline is cloned from the master template. </h4>
<img src="https://user-images.githubusercontent.com/2539627/69100727-b0a01300-0a55-11ea-8633-021e166e1fbd.png"/>



<h4>Live status update </h4>
Each PR will receive live status update on the CodePipeline actions.
<img src="https://user-images.githubusercontent.com/2539627/69098643-e55d9b80-0a50-11ea-9952-113913f4dab5.png">


<h3>FAQ</h3>
<h5>Does TerraPy deletes the pipeline when the PR is closed?</h5>
Yes, when a PR is closed TerraPy deletes the pipeline.

<h5>What permissions does TerraPy needs to have </h5>
1. SSM Parameter store
2. CodePipeline
