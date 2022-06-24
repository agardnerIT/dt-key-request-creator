# Dynatrace Key Request Creator Tool

Programatically define key requests in Dynatrace.

This tool can be used to define key requests BEFORE traffic is present on the endpoints.

## Usage

1. Create a DT API token with `read entities` and `write settings` v2 permissions
2. Create an input file (eg. `input.csv`). Note that pipes are separators.
   `request_name` must match what is shown visually in Dynatrace so if request naming rules are used, use the visual output to match whatever is shown in DT.

```
entitySelector|request_name
type(SERVICE),tag(app:frontend)|/pageOne.html
type(SERVICE),tag(app:frontend),tag(environment: production)|/pageTwo.html
type(SERVICE),tag(app:frontend)|/pageThree.html
type(SERVICE),tag(app:frontend)|/pageFour.html
```

For example: `/pageOne.html` will be marked as a KR for any service tagged with `app: frontend`.

2. Run as a docker image:
```
docker run --rm \
-v $(pwd):/app \
-e dt_filename=input.csv \
-e dt_url=https://abc12345.live.dynatrace.com \
-e dt_api_token=dt0c01.********** \
gardnera/dt-key-request-creator:0.1.0
```
