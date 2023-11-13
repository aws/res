## Create Application

Create a web-based workflow to submit your HPC jobs.

<details>
    <summary markdown="span"><b>Step1: Design the job submission form</b></summary>

To customize your web form, click **"Form Builder"** tab.

#### Add a Form field

To add a new form field, click **"Add Form Field"** button. This will add a new field at the bottom of the form. Click **"Edit"** button to customize your HTML component.

You can choose from multiple HTML components such as:

-   Headings (size 1 to 5)
-   Text area
-   Number
-   Select
-   Text
-   Toogle
-   Password

#### Edit a form field

Select the HTML component you want to edit and click the **"Edit"** icon on the right side of the panel.

#### Duplicate a form field

Select the HTML component you want to copy and click the **"Duplicate"** icon on the right side of the panel.

#### Delete a form field

Select the HTML component you want to delete and click the **"Delete"** icon on the right side of the panel.

#### Hide/Show Elements:

You can hide/show HTML elements based on the value of other elements via the **when** clause.

---

**Example1**: You have a dropdown menu named "dropdown1" you want to show only when the user click on the toggle button "checkbox1":

```json
{
    /*
 1 - Click Form Builder (Advanced Mode using JSON)
 2 - Locate the HTML element you want to edit
*/
    "param_type": "select",
    "name": "dropdown1",
    /* Add the "when" block below */
    "when": {
        "param": "checkbox1",
        "eq": true
    }
}
```

---

**Example2:** You have a dropdown menu named "dropdown1" you want to show only when the user specify a number of CPUs (via `ncpus` HTML field) lower than 5:

```json
/*
 1 - Click Form Builder (Advanced Mode using JSON)
 2 - Locate the HTML element you want to edit
*/
{
    "param_type": "select",
    "name": "dropdown1",
    /* Add the "when" block below */
    "when": {
        "param": "ncpus",
        "lt": 5
    }
}
```

-   **when** block works for all **param_type**
-   Here is a list of all comparators you can use:
    -   eq
    -   not_eq
    -   in
    -   not_in
    -   gt
    -   gte
    -   lt
    -   lte
    -   min
    -   max
    -   range
    -   not_in_range
    -   regex
    -   not_regex
    -   exact
    -   starts_with
    -   ends_with
    -   empty
    -   not_empty

</details>

<details>
    <summary markdown="span"><b>Step2: Design the job script</b></summary>

Once you have designed your HTML form, it's time to create the associated job script.
This script will be the actual command executed by the scheduler host.

#### Script Interpreter

You can choose whether you want your script to be executed as a regular Linux Shell Script (via **/bin/bash**) or directly as a OpenPBS queue file (executed via **qsub**)

#### Script Template Type

In the **Simple** mode, you can substitute the variables returned by the HMTL form using **%variable%**. For example, if you have one HTML field named **ncpus**, you can retrieve the value entered by the user via **%ncpus%**.

In the **Advanced** mode, you can leverage Jinja templating to build advanced logic. For example, **{{ job | upper }}** will retrieve the HTML field named **job** and enforce uppercase.

#### Job Script

This is where you will add the logic you want to be executed.

</details>

<details>
    <summary markdown="span"><b>Step 3: Create the application profile</b></summary>

Once your HTML form and job script are ready, choose a name for your application and upload a thumbnail.

</details>
