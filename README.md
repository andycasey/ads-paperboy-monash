Monash Paperboy
---------------

Search for recently published papers by Monash physicists and astrophysicists,
and prepare a summary document containing the first page of recnetly published
papers so that they can be put on display within the Monash School of Physics
and Astrophysics.


Installation
------------

Clone this repository using this terminal command:

    git clone git@github.com:andycasey/ads-paperboy-monash.git paperboy
    cd paperboy/

Installing required Python packages
-----------------------------------

The code requires a few custom Python packages which can be installed with the 
following terminal command:

    pip install requests ads pdfrw


Getting an ADS key
------------------

The NASA Astrophysics Data System (ADS) has an Application Programmer Interface 
(API) which allows us to run programmatic queries against their database. This 
service puts load on the ADS servers, and therefore could be overloaded by
unscrupulous users making too many requests. Therefore you will need to get a 
unique API token from ADS. We will use that token for all of the requests we 
make to ADS.

Here is how to get an API key from ADS:

  1. Sign up for an account on the [newest version of ADS](https://ui.adsabs.harvard.edu).

  2. Log in to your new account and navigate to [API Token](https://ui.adsabs.harvard.edu/#user/settings/token),
     and then click *Generate a new key*.

  3. Create a folder called `.ads` (the dot is necessary) in your home 
     directory and create a new file in the `.ads` folder called `dev_key`. 
     Save your generated key to the `dev_key` file.


Run the script
--------------

Now you should be able to run the `paperboy.py` script using the following 
terminal command:

    python paperboy.py 

This should produce some output to the terminal, and send an email with the 
papers published from the previous month. You can also specify the year and
month to search. For example:

    python paperboy.py 2014 8

Will search for papers published by Monash researchers in the month of August,
2014.


Set up a monthly `cron` job to run the script automatically
---------------------------------------------------------

At a terminal, type:

    crontab -e

And enter in the following line:

    0 7 1 * * python <YOUR_FOLDER>/paperboy.py > <YOUR_FOLDER>/paperboy.log

Then the code will run at 07:00 AM on the first day of every month. The 
`<YOUR_FOLDER>` expression above refers to the folder location where this script
lives on your local system. 

Note that the `paperboy.py` script will also send the summary PDF to the nearest
printer (using the `lp` system command), but you will need to swipe your access
card at a physical Monash printer in order to release the job from the queue,
just like any other print job.
