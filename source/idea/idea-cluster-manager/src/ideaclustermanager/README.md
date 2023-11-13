# Digital Engineering Portal on AWS

# Documentation

https://docs.ide-on-aws.com

# Directories

## app

Contains the source for the Cluster Manager app.

### accounts

#### db
Contains the database object classes for each DynamoDB database. Each database object file creates and manipulates its respective database.

#### helpers

Contains a preset computer helper which is used to manage creating preset Computer Accounts in AD using the adcli

#### ldapclient

Contains the source for the ldap files. There are two different LDAP class in their own files, one for AD and one for OpenLDAP. They share a common bastract parent class and an ldap client factory that builds them.

#### accounts_tasks.py

Contains the various tasks for the accounts service. These tasks are called when the task manager service picks up an accounts task from the tasks queue and invokes the task.

#### accounts_service.py

Contains the accounts service, this service is called when the api receives a call related to accounts (i.e accounts api or auth api).

#### ad_automation_agent.py

Contains the Active Directory Automatino Agent Service. This manages password rotation of AD Admin credentials and manages automation for creating preset computers using adcli for cluter nodes. It is expected that admins would heavily customize the implementation.

#### auth_constants.py

Contains constants related constants. Contains the default login shell, the user home directory and the allowable username regex.

#### auth_utils.py

Contains various utility functions related to auth such as sanitization of parameters, checking for invalid operations, and verifying if the username is one of the not allowed list (i.e. root, admin, ec2-user).

#### cognito_user_pool.py

Contains the class used to manipulate and read from the cognito user pool.

#### user_home_directory.py

Contains the class used to create and manipulate the user home directory, including accessing and creating ssh keys.

### api

Contains the various API files for each api. The files contain the acl to define the scope of each action. When the api is invoked, it calls the respective function. The function will then call the respective function from the service that contains the action to be performed.

#### accounts_api.py

Contains the API for creating and manipulating accounts and groups. The api functions all call the functions from the accounts service.

#### analytics_api.py

Contains analytics API. The only action in this API is to query OpenSearch. The analytics service it uses is set in the SocaContext which is defined in the idea sdk and is the parent class of the app_context.

#### api_invoker.py

Contains the entrypoint for the API. When a request is received on the api server, it calls the api invoker, which then invokes the respective API.

#### auth_api.py

Contains the API for various authorization actions such as changing passwords, handling forgotten passwords, etc.

#### cluster_settings.py

Contains the API for getting information about the modules and cluster settings. It does not user a service but rather reads from the config files, the DynamoDB modules and cluster-settings tables, and uses botocore to get EC2 instance information. 

#### email_templates_api.py

Contains the for manipulating and creating email templates in the email-templates DynamoDB database.

#### projects_api.py

Contains the API for creating and manipulating projects. Projects are permission boundaries in which users and groups can be added.

### email_templates

Contains files related to the email templates service.

### notification

Contains files related to the notifications service. This service reads from the notifications SQS queue and sends emails via SES.

### projects

#### db

Contains the database object files for the various databases used in the projects service. These files create and manipulate the DynamoDB databases.

#### project_tasks.py

Contains the project tasks. The tasks are invoked after the task manager picks up a related projects tasks from the tasks SQS queue.

#### projects_service.py

Contains the functions the main functionality for the projects service.

### tasks

Contains the task manager which sends tasks to the tasks SQS queue, reads from the tasks SQS queue, and routes picked up tasks to the appropriate service task.

### app_context.py

Contains the application context, uses SocaContext as a base class. This is passed to the ClusterManagerApp. 

### app_main.py
The entrypoint for the Cluster Manager app. This creates an instance of ClusterManagerApp.

### app_messages.py

Contains the html as a variable for the developer mode index page.

### app_utils.py

Contains various utility functions used throughout the Cluster Manager App.

### cluster_manager_app.py
Contains the ClusterManagerApp class. This is what is created when from the entrypoint of the app. This initializes and starts the app including the api, servers, services, etc.

### web_portal.py

Contains the WebPortal class. This is used to intiate the web portal which involves adding routes to the http_app server to define a function to run when routes are hit, as well as adding a static path to define where the webapp directories exist.
 
## cli

Contains the Cluster Manager CLI. The cli is used as an alternative method of making Cluster Manager API calls.
