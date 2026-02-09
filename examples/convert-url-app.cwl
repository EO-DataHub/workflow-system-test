$graph:
- class: Workflow
  doc: Convert URL
  id: test-convert-url--15-00-00
  inputs:
    fn:
      default: resize
      doc: the operation to perform
      label: the operation to perform
      type: string
    size:
      default: 50%
      doc: the percentage for a resize operation
      label: the percentage for a resize operation
      type: string
    url:
      default: https://raw.githubusercontent.com/EO-DataHub/test-workflow-store/main/EO-Data-Hub-logo_colour_425px.png
      doc: the image to convert
      label: the image to convert
      type: string
  label: convert url app
  outputs:
  - id: converted_image
    outputSource:
    - convert/results
    type: Directory
  requirements:
    ResourceRequirement:
      coresMax: 1
      ramMax: 1024
  steps:
    convert:
      in:
        fn: fn
        size: size
        url: url
      out:
      - results
      run: '#convert'
- baseCommand: convert.sh
  class: CommandLineTool
  hints:
    DockerRequirement:
      dockerPull: eoepca/convert:latest
  id: convert
  inputs:
    fn:
      inputBinding:
        position: 1
      type: string
    size:
      inputBinding:
        position: 3
      type: string
    url:
      inputBinding:
        position: 2
        prefix: --url
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
s:softwareVersion: 0.1.2
schemas:
- http://schema.org/version/9.0/schemaorg-current-http.rdf
