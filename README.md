# Hosted AutoML Export Transformer (Hamlet)

## Auto ML Export

## Subject Assistant

Hamlet has an export feature that ties into the Zooniverse Machine Learning Subject Assistant, [(app)](https://subject-assistant.zooniverse.org/) [(source)](https://github.com/zooniverse/zoo-ml-subject-assistant) which lets project owners/researchers submit their camera trap photos to an external Machine Learning (ML) service, which in turn finds animals in those images.

### User Story

The user story is as follows:
- Users start at the Subject Assistant app.
- Users are directed to Hamlet, where they choose a Subject Set to export to the external ML Service.
- Hamlet performs the export feature, and provides users with a link back to the Subject Assistant with an "ML Task ID" - e.g. `https://subject-assistant.zooniverse.org/#/tasks/6378`
- Users click that link, and process the ML-tagged photos on the Subject Assistant app.

### External Dependencies

The Subject Assistant requires the following external systems:

- Machine Learning Service - in this case, powered by Microsoft.
- an Azure Storage Container - works in conjunction with the ML Service, which requires "subject manifest" files to be stored on Azure.

As of Dec 2019, these external services are provided by our friends in Microsoft.

### Environmental Variables

The Subject Assistant feature requires the following ENV variables defined:

- `SUBJECT_ASSISTANT_AZURE_ACCOUNT_NAME`
- `SUBJECT_ASSISTANT_AZURE_ACCOUNT_KEY`
- `SUBJECT_ASSISTANT_AZURE_CONTAINER_NAME`
- `SUBJECT_ASSISTANT_ML_SERVICE_CALLER_ID` - provided by our friends in Microsoft who run the ML Service.
- `SUBJECT_ASSISTANT_ML_SERVICE_URL` - ditto

Optionally, the following ENV variables can be defined:

- `SUBJECT_ASSISTANT_EXTERNAL_URL` - defaults to `http://subject-assistant.zooniverse.org/#/tasks/`

### Mechanics: Django Pages/Views

The ML Subject Assistant feature in Hamlet has two views:

- `GET /subject-assistant/<int:project_id>/` - lists all the Subject Sets for a Project, along with their "ML export" status and (if the export is successful) a link back to the Subject Assistant app.
- `POST /subject-assistant/<int:project_id>/subject-sets/<int:subject_set_id>/` - performs the ML Export action for a given Subject Set, then redirects users back to the listing page.

### Mechanics: Database Model

The `MLSubjectAssistantExport` table has the following fields:

- subject_set_id - the ID of the Zooniverse Subject Set that was exported to the external ML Service
- json - the "subject manifest" file, in JSON format, created from all the Subjects of the Subject Set. The format is specific to the ML Service.
- azure_url - the URL of the "subject manifest" file that was uploaded to an external Azure storage container. (See Mechanics: ML Export Action for why)
- ml_task_uuid - the task request ID or "job ID" for the ML Export action. This is generated by the external ML Service.

### Mechanics: ML Export Action

Mechanically, the ML Subject Assistant's "export to Microsoft" action performs the following:

1. get all the Subjects for a given Subject Set (pulling from Panoptes)
2. create a JSON file - the "subject manifest" - that describes the Subjects to be exported, in a format specified by the external ML Service.
3. upload the JSON file to an external Azure storage container (reason: the current external ML Service only reads subject manifest files from Azure), then create a "shareable URL" to that JSON file. (Clarification: Azure uses a SAS or Shared Access Signature tokens to create shareable URLs with limited lifespans.)
4. Submit the shareable URL to the ML Service, and get the "job ID" it returns.

The Job ID plus the known Subject Assistant app URL is all that's required to construct a "return URL" for the user.
