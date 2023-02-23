# ns1
Helper scripts for NS1

# nsone-reports.py
## Description
Script for viewing activity report in stdout or sending it via email.

## Usage
```
nsone-reports.py [-h] [--unit {days,seconds,microseconds,milliseconds,minutes,hours,weeks}] [--amount AMOUNT]
                 [--limit LIMIT] [--config CONFIG] [--export] [--format {json,xml,csv,pdf,xlsx,html}]
                 [--mailfrom MAILFROM] [--mailto MAILTO] [--silent]

options:
  -h, --help            show this help message and exit
  --unit {days,seconds,microseconds,milliseconds,minutes,hours,weeks}
                        set unit for timestamp calculation (default: hours)
  --amount AMOUNT       set number of units for timestamp calculation (default: 1)
  --limit LIMIT, -l LIMIT
                        limit number of returned records (default: 20)
  --config CONFIG       path to config file
  --silent, -s          don't print report to stdout

  --export, -e          export report in same format as in NS1 gui
  --format {json,xml,csv,pdf,xlsx,html}
                        filetype of generated report (default: json)

  --mailfrom MAILFROM   sender address
  --mailto MAILTO       recipient address separated by comma (default: None)
  ```
  
  ## Configuration
  Check the [example-config.ini](../master/example-config.ini) for available configuration options.
