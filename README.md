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

## Repo structure

The command below was used for the tree diagram
```
tree -L 3 --gitignore
```

This is the repo structure:
```
.
├── docs
│   └── plan.md
├── libraries.txt
├── README.md
└── src
    ├── core
    │   ├── api.py
    │   ├── cli.py
    │   ├── library.py
    │   └── series.py
    └── storage

5 directories, 7 files
```

***src*** contains all code logic with ***core*** storing core python files and ***storage*** being used for user data storage. ***docs*** folder is all the documentation, project plans and explanations behind its inner workings. ***libraries.txt*** contains a list of libraries used for install.


## Libraries and tools

#### Libraries:
- requests for API requests
- click for CLI

#### API
Since this project doesn't have its own tv databse an open API was used. Namely [tv maze api](https://www.tvmaze.com/api)

#### UML

The UML diagrams were used in this project. The way I made them is the **graphore** Linux app that is free and easily available. 