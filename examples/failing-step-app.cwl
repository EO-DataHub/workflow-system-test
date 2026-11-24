# A workflow whose only step always fails, used to check that failures are reported.
$graph:
- class: Workflow
  doc: Fail on purpose
  id: test-failing-step
  inputs:
    message:
      default: failing on purpose
      doc: the message printed before failing
      label: the message printed before failing
      type: string
  label: failing step app
  outputs:
  - id: results
    outputSource:
    - fail_on_purpose/results
    type: Directory
  requirements:
    ResourceRequirement:
      coresMax: 1
      ramMax: 1024
  steps:
    fail_on_purpose:
      in:
        message: message
      out:
      - results
      run: '#fail'
- arguments:
  - -c
  - echo "$0"; exit 1
  baseCommand: sh
  class: CommandLineTool
  hints:
    DockerRequirement:
      dockerPull: eoepca/convert:latest
  id: fail
  inputs:
    message:
      inputBinding:
        position: 1
      type: string
  outputs:
    results:
      outputBinding:
        glob: .
      type: Directory
  requirements:
    ResourceRequirement:
      coresMax: 1
      ramMax: 512
$namespaces:
  s: https://schema.org/
cwlVersion: v1.0
s:softwareVersion: 0.1.0
schemas:
- http://schema.org/version/9.0/schemaorg-current-http.rdf
