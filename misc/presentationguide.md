# Technical guide for presentation

## Preperation

1. Reset Database by replacing database in root folder with database in presentation folder 

2. Run programme in replit.

3. You can find sample login ICs in profile_ic.txt. Password is not checked, but some character needs to be entered.

## Medic View
1. Point to /home (automatically redirects from root page)
2. Click 'Login with SingPass', then enter a valid or invalid NRIC. Type anything in the password field.
3. Valid medic card will be shown, or site will redirect to /home
4. Click logout to return to home

## Unit View
1. Point to /inet 
2. Click 'Login with SingPass', then enter a valid or invalid NRIC (see the Profile table in eMedicIntranet.db. Type anything in the password field.
3. Unit View will be shown, or site will redirect to /home
4. Click logout to return to home

## SMTI View
Same as Unit view, but select user that has SMTI rights.

## Profile View
After entering SMTI View, select the Profile table

## Function Lists

### Excel Loading
#### Available in Unit, SMTI and Profile View
1. Download TEST3.xlsx (to demonstrate query) or TEST$.xlsx (to demonstrate modification, for SMTI and Profile View only) from the presentation folder
2. Select choose file
3. Click upload after file is chosen
4. Click search or modify

### Query
#### Available in Unit, SMTI and Profile View
1. Populate the query field with an Excel or enter it manually
2. Select Search
3. Features to highlight: If profile does not exist or data does not exist for that particular prodile, all fields will be Invalid except for Full Name and Masked NRIC. 

### Download Table
#### Available in Unit, SMTI and Profile View
If Download button is present, table will be downloaded as an .xlsx file.

### Table functions
#### Available in Unit, SMTI and Profile View
Tables have identical features
1. Sort according to columns
2. Select columns that can be visible.

### Modify Database
#### Available in SMTI and Profile View
1. Populate the query field with an Excel (modify1.txt shows basic features, while modify2 shows a delete feature)
2. Select Modify
3. If errors pop up, change the features accordingly. Errors will pop up if the profiles are invalid or data formatting is incorrect.
4. A modal will appear with the accepted changes. Select Confirm Modifications to accept the changes
5. After the database is modified, a table showing the final changes is shown.