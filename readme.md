# SMTI eMedic card
![SMTI eMedic card logo](./static/icon.png)

Intern: Ng Ri Chi (May-August 2021)

Supervisor: Hang Kher Lee

SMTI eMedic card aims to replace the physical Medic card carried by SAF Medics. The webportal is built on Flask, Flask-WTF and Flask-SQLalchemy. The database is based on SQLlite and the CSS library used are Bootstrap and Bootstrap Table.

## Content
1. Quick start
2. Structure of Application
3. Database and Models
4. Forms
5. Views and User Management
6. Query and Modifying

## Quick start
This web portal was built from Replit, and its best to run it there. You can make a new Repl by directly copying it from the Repl or the GitHub repository. Afterwards, press run and the server will automatically set up.

## Structure of the Application
Take note that this project does not make use of Flask Blueprint to compartmentalise the code. The project, however, is lightly compartmentalised although full use of Flask Blueprint is a logical next update.

### Database and Models
This project has three separate database, which are described in the programme in the models.py file. 

### Forms
Forms in this project are described in the forms.py file.

### Views and User Management
Rendering and processing of pages and user inputs, as well as a primitive version of User Authorisation are contained in the main.py file. HTML files and templates can be found in the templates folder while image files can be found in the static folder.

## Database and Models
There are three databases:

1. eMedicInternet.db and eMedicIntranet.db store the medic and administrator data. The two database are separate to mimic an internet and intranet facing server.
2. The last database is FakePass.db, to mimic a SingPass server.

The database are managed in the application using SQLalchemy, and the models are described in models.py. 

A detailed breakdown of the models and what they mean can be found in ./misc/dataprofiles.xlsx

Data for this are randomly generated (see ./misc/profile_generator.xlsx) or are sourced from https://api.singpass.gov.sg/library/myinfo/developers/resources-personas

## Forms
Forms are described in forms.py.

## Views and User Management

Views are stored in the main.py file. 

Some views can be accessed by any user, for instance / (redirects to home), /home, /inet, /terms and /404

/singpass can only be accessed from /home or /inet

/medic can only be accessed after an authorised user authenticates from /home. Authorisation is first checked with the existance of the IC in FakePass.db, then whether user has a course_date or ampt_date value.

/smti and /unit can only be accessed after an authorised user authenticates from /inet. Authorisation is first checked with the existance of the IC in FakePass.db, then the rights value. 

If users cannot be authenticated, the user will be redirected back to its original landing page.

The state of the user is stored in session[state]. The user management system is rudimentary and is also ripe for an upgrade.

## Query and Modifying

### User inputs
The portal can read a user's excel file, which will populate the query field. The query field can also be populated manually. 

### Medic Query
When the Medic view receives the UUID after the user logs in, it would then try to load the data values and use expiryCalculator in helper.py to calculate the medic's expiry date. If no user is found, the try will exit with an exception, where /home will load with an error message.

### Unit/SMTI/Profile Queries
Administrators access UUID indirectly through matching the full name of a person with the masked IC. If there are no matches, an Invalid will be returned. If there are more than one match, the UUIDs will be loaded in sequence.

The UUID will then be matched and joined. Finally, the data will be arranged in sequence of the query that is in the input so that the user will not be disorientated.

The output table can also be downloaded with sendExcel in helper.py. Also, take note that the first row is used as a column indicator and as the columns are fixed, it will not be read.

### SMTI/Profile Modify
Unlike Queries where headers do not matter, headers matter in profiles. Follow the headers indicated in red on the Query result table to modify the database.

Adding and Changing uses SQLAlchemy's merge function, while Delete uses the delete function.

FakePass.db is assumed to have a perfect set of identities, so it is excluded from any modification.

#### Modification Checks
Before any changes to the database is made, checks are done. Most basically, a uuid header is necessary. If the profile does not exist, a full_name and masked_ic field must be supplied to create a new profile. The data must also be in the specified format in Data Profiles.

#### Adding
To add a new user, you need to define the uuid, full_name and masked_ic. Only modification of columns in the specific View is permitted to reduce error.

#### Changing
Only modification of columns in the specific View is permitted to reduce error.

#### Deleting
When deleting, only specified columns are deleted. A check will be done if any deletion occurs, and if the profile has no more parameters, the whole profile (ie including masked_ic and full_name) will be deleted. This is the only way to remove masked_ic and full_name.

#### Ignore
To ignore a column for a particular profile, leave the cell blank.