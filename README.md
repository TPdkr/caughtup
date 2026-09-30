# CAUGHT UP

Get a nice CLI to get info on series you like and get info when they get updated with new seasons info and such!

App is designed to be simple, yet practical. If you have any ideas please share them with me directly!

## Set up

In order to set up the app just download the libraries using the command below in the terminal:

```
pip install -r libraries.txt
```

Then just go to the ***src/core*** and run the ***cli.py*** file. It contains all CLI logic of the app.

Done. Enjoy!

All your profile info is stored locally in the ***src/storage*** folder in a json file with your profile name. So, if you want to open
it on a new device or change it directly you can edit,move or copy the file.

### Making launching the app easier

If you want to be able to just run the command below to launch the app you should do 1 more step.
```
caughtup
#app is launched from this 1 command in any directory
```

To make this work give the shell scripts in the repo execution permissions and run the set up script.
```
chmod +x *.sh
./define_caughtup_perm.sh
```


## Repo structure

The command below was used for the tree diagram
```
tree -L 3 --gitignore --dirsfirst
```

This is the repo structure:
```
.
├── docs
│   ├── activity_diagram_outline.png
│   ├── activity_diagram.png
│   ├── activity.gaphor
│   ├── calsses.gaphor
│   ├── classes_outline.png
│   ├── classes.png
│   ├── interaction.png
│   ├── plan.md
│   ├── user_interaction.gaphor
│   └── user_interaction.png
├── src
│   ├── core
│   │   ├── api.py
│   │   ├── cli.py
│   │   ├── library.py
│   │   └── series.py
│   ├── storage
│   └── test
│       ├── test_cli.py
│       ├── test_library.py
│       └── test_series.py
├── define_caughtup_perm.sh
├── define_caughtup.sh
├── libraries.txt
├── README.md
└── run_caught_up.sh

6 directories, 22 files
```

***src*** contains all code logic with ***core*** storing core python files and ***storage*** being used for user data storage. ***docs*** folder is all the documentation, project plans and explanations behind its inner workings. ***libraries.txt*** contains a list of libraries used for install.

At the same time the shell scripts are used to simplify the use of the app for the end user.

## Libraries and tools

#### Libraries:
- requests for API requests
- click for CLI

#### API
Since this project doesn't have its own tv databse an open API was used. Namely [tv maze api](https://www.tvmaze.com/api)

#### UML

The UML diagrams were used in this project. The way I made them is the **graphore** Linux app that is free and easily available. 