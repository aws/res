## Create Queue Profile

Create a new queue profile

### Step1: Queue Profile Info

#### Basic Info

Choose a name and a friendly title for your queue profile. You will then need to associate existing projects to the queue. Only members that belong to the project(s) will be able to interact with the queues.

#### Operating Mode

Choose the scheduler queue(s) to associate to the profile. Queue(s) will be automatically created if they do not exist.

#### Queue Limits

If needed, configure the maximum number of concurrent running jobs / provisioned instances running on all queues of the profile.

#### Queue ACLs

Choose the type of EC2 instances that can be deployed by the users. You can also specify a list of restricted parameters that your users won't be able to change. You can also have a list of additional security groups / IAM instance profiles that can be deployed for the jobs.
