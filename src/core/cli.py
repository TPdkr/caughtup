import click
import sys

# import custom classes
from series import Series, Status
from library import Library
from api import Api

def mask_path(path):
    '''
    Mask the path/profile name to make it easier for the user

    Args:
        path: string name of the profile
    '''
    return "../storage/"+path+".json"

def load_profile():
    """
    Load profile or create a new one. 

    Returns:
        lib: profile to be used
    """
    print("loading profile")
    while True:
        if click.confirm("Create a new profile?", default=False):
            #create a new profile and set its path
            path = click.prompt("Enter path where to create profile: ")
            path = mask_path(path)
            lib = Library()
            lib.set_path(path)
            print("user profile created")
            return lib
        else:
            try:
                #a correct path should be entered
                path = click.prompt("Enter path to your series library file: ")
                path = mask_path(path)
                lib = Library(path=path)
                print("user profile loaded")
                return lib
            except FileNotFoundError:
                #in case the path is incorrect
                continue

def main():
    profile = load_profile()
    user_loop(profile)            
        
@click.group()
def cli():
    pass

"""
MAIN LOOP
Here all key commands can be entered by the user.
"""
def user_loop(profile):
    ACTIONS = ["list", "add", "update-all", "clear-updated", "get-tags",
               "caught-up-all", "reset-all", "set-profile", "set-path", "exit"]
    
    while True:
        choice = click.prompt("\nACTION", type=click.Choice(ACTIONS, case_sensitive=False))
        #read arguments entered by user
        if choice == "exit":
            break

        #we try to execute the command, but also catch exceptions
        try:
            cli.main(args=[choice], obj=profile, standalone_mode=False)
        except click.ClickException as e:
            e.show()
        except click.exceptions.Exit:
            pass  # subcommand finished normally

    profile.save()
    click.echo(f"Changes saved into {profile.path}.")

@cli.command("list")
@click.pass_obj
def list_series(profile):
    '''
    list series in the library with the specific parameters

    Args:
        profile: user data
        tag: tag to search for
        updated: search for updated tag
        keyword: name should include this keyword
    '''
    click.echo("")
    tag = click.prompt("(ENTER to skip) Tags to include", default="")
    tag = tag or None
    updated = click.confirm("(ENTER to skip) List only updated series", default=False,show_default=True)
    keyword = click.prompt("(ENTER to skip) Key word to search for ", default="")
    #find the matches list
    matches = profile.get_with(keyword, tag, updated)
    matches = sorted(matches, key=lambda m: m.premiered, reverse=True)

    #check for matches being empty
    if not matches:
        click.echo("No series found.")
        return
    
    #print the results out
    click.echo(click.style(f"{"i":>2}|{"name":<34}|premiered    | {"progress":<26}| TAGS", fg="green"))
    for i,match in enumerate(matches):
        click.echo(click.style(f"{i:>2} ", fg="green"), nl=False)
        click.echo(click.style(f"{match.name:<35} {match.premiered:<12}| ", fg="blue"), nl=False)
        click.echo(f"s:{match.num_seasons:>2} ep:{match.num_episodes:>3} - at {str(match.stopped_at):>8} | ", nl=False)
        click.echo(click.style(f"{match.tags}", fg="yellow"))

    #prompt user for next action
    choice = click.prompt(f"ACTIONS [idx] [back]")
    choice = choice.split()
    if len(choice)==1 and choice[0].isdigit():
        idx = int(choice[0])
        if 0 <= idx < len(matches):
            series_menu(profile, matches[idx])
        else:
            click.echo("Invalid index")

@cli.command("add")
@click.pass_obj
def add_series(profile):
    '''
    This function adds a series by searching for it and
    making a choice between results

    Args:
        profile: user data
    '''
    #user needs to enter the search query here
    query = click.prompt("Enter the search query: ")
    matches = Api.search(query)

    if not matches:
        click.echo("No series found.")
        return

    matches = [Series(el) for el in matches]
    #display the matches
    for i, match in enumerate(matches):
        click.echo(click.style(f"{i:>2} ", fg="green"), nl=False)
        click.echo(click.style(f"{match.name:<25} {match.premiered:<12}; ", fg="blue"))
    #choice of index to add
    index = click.prompt("Enter desired index: ",type=click.IntRange(0, len(matches) - 1))
    profile.add_series(matches[index])

@cli.command("set-profile")
@click.pass_obj
def set_profile(profile):
    print("setting default  profile")

@cli.command("set-path")
@click.pass_obj
def set_path(profile):
    path = click.prompt("Enter new path (name.json): ")
    path = mask_path(path)
    profile.set_path(path) 
    print("Saving path changed")

@cli.command("update-all")
@click.pass_obj
def update_all(profile):
    print("Fetching data for updates")
    profile.check_for_updates_all()
    print("Updates completed")

@cli.command("clear-updated")
@click.pass_obj
def clear_updated(profile):
    print("Removing updated status")
    profile.clear_updated()

@cli.command("caught-up-all")
@click.pass_obj
def caught_up_all(profile):
    print("Set every series as all caught up")
    profile.all_caught_up_all()

@cli.command("reset-all")
@click.pass_obj
def reset_all(profile):
    if click.confirm("This will reset watch progress for ALL series. Continue?"):
        profile.reset_all()
        click.echo("Done.")
    else:
        click.echo("Cancelled.")

@cli.command("get-tags")
@click.pass_obj
def get_tags(profile):
    tags = profile.get_tags()
    click.echo(click.style(f"TAGS={tags}", fg="yellow"))

"""
SERIES DATA FOR 1 SERIES
When a series from list is selected its index is passed and actions can be performed
on it.
"""

def series_menu(profile, serie):
    """
    SERIES DATA MENU
    User can do the following from here:
    - remove
    - add/remove tags
    - set stopped at
    - set all caught up
    """
    ACTIONS = ["back","add-tag", "remove-tag", "set-stopped-at","caught-up","remove","reset"]

    while True:
        #PRINT SERIES
        #status label is retrieved as a string
        STATUS_STYLE = {
            Status.CAUGHT_UP: ("CAUGHT UP", "green"),
            Status.IN_PROGRESS: ("WATCHING", "yellow"),
        }
        label, color = STATUS_STYLE.get(serie.status, ("NOT STARTED", "red"))
        #show the series data
        click.echo(click.style(f"\n{serie.name.upper()}", bg="blue", fg="white"))
        click.echo(click.style(f"premiered: {serie.premiered}\nended: {serie.ended}",fg="blue"))
        click.echo(f"s:{serie.num_seasons} ep:{serie.num_episodes} - at ({serie.stopped_at[0]}, {serie.stopped_at[1]})")
        click.echo(click.style(f"TAGS={serie.tags}", fg="yellow"))
        click.echo("STATUS: " + click.style(label, fg=color, bold=True))

        #ASK FOR ACTION
        #the options available to the user
        action= click.prompt("\nACTION:", type=click.Choice(ACTIONS, case_sensitive=False), default="back")

        if action == "back":
            return

        #checking which action was chosen
        if action == "remove":
            if click.confirm("Are you sure you want to delete the info?"):
                profile.remove_series(serie.id)
                click.echo(f"Removed {serie.name}")
            else:
                print("Cancelled")
            return  # object no longer exists, so leave the loop

        #tag actions
        elif action == "add-tag":
            tag = click.prompt("Enter tag name")
            serie.add_tag(tag)
            click.echo(f"Tagged {serie.name} with {tag}")
        elif action == "remove-tag":
            tag = click.prompt("Enter tag name")
            serie.remove_tag(tag)
            click.echo(f"Removed tag {tag}")

        # user progress changes
        elif action == "set-stopped-at":
            s = click.prompt("Season",type=click.IntRange(0, serie.num_seasons))
            ep = click.prompt("Episode", type=click.IntRange(0,100))
            serie.set_stopped_at([s, ep])
            click.echo(f"Updated stopped_at to {s} {ep}")
        elif action == "caught-up":
            serie.all_caught_up()
        elif action == "reset":
            serie.reset()
        #oopsieees
        else:
            click.echo("Unrecognized action")

"""
MAIN FUNCTION
"""
if __name__ == "__main__":
    main()