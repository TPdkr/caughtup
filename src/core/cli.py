import click
import sys

# import custom classes
from series import Series, Status
from library import Library
from api import Api

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
            path = "../storage/"+path
            lib = Library()
            lib.set_path(path)
            print("user profile created")
            return lib
        else:
            try:
                #a correct path should be entered
                path = click.prompt("Enter path to your series library file: ")
                path = "../storage/"+path
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
    while True:
        choice = click.prompt(
            "\n[list] [add] [set-profile] [set-path] [get-tags] [caught-up-all] [reset-all] [exit]",
            default="",
            show_default=False,
        )
        #read arguments entered by user
        args = choice.split()
        #check that 1. non empty 2. not exit condition
        if not args:
            continue
        if args[0] == "exit":
            break

        try:
            cli.main(args=args, obj=profile, standalone_mode=False)
        except click.ClickException as e:
            e.show()
        except click.exceptions.Exit:
            pass  # subcommand finished normally

    profile.save()
    click.echo(f"Changes saved into {profile.path}.")

@cli.command("list")
@click.option("--tag", default=None)
@click.option("--updated", is_flag=False)
@click.option("--keyword", default="")
@click.pass_obj
def list_series(profile, tag, updated, keyword):
    print(f"listing series with tag:{tag} updated:*{updated}* key_word:*{keyword}*")
    matches = profile.get_with(keyword, tag, updated)
    print(matches)
    for i,match in enumerate(matches):
        click.echo(click.style(f"{i} ", fg="green"), nl=False)
        click.echo(click.style(f"{match.name} {match.premiered}; ", fg="blue"), nl=False)
        click.echo(f"s: {match.num_seasons} ep: {match.num_episodes} - at {match.stopped_at}")

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
    #user needs to enter the search query here
    query = click.prompt("Enter the search query: ")
    matches = Api.search(query)

    matches = [Series(el) for el in matches]

    for i, match in enumerate(matches):
        click.echo(f"{i} {match.name} {match.premiered};")

    index = click.prompt("Enter desired index: ")
    if index.isdigit():
        profile.add_series(matches[int(index)])
    else: 
        click.echo("Invalid input")

@cli.command("set-profile")
@click.pass_obj
def set_profile(profile):
    print("setting default  profile")

@cli.command("set-path")
@click.pass_obj
def set_path(profile):
    path = click.prompt("Enter new path (name.json): ")
    path = "../storage/"+path
    profile.set_path(path) 
    print("Saving path changed")

@cli.command("caught-up-all")
@click.pass_obj
def caught_up_all(profile):
    print("Set every series as all caught up")
    profile.all_caught_up_all()

@cli.command("reset-all")
@click.pass_obj
def reset_all(profile):
    print("resetting watch progress")
    profile.reset_all()

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
    while True:
        click.echo(click.style(f"\n{serie.name.upper()} ({serie.premiered});\n", bg="blue", fg="white"))
        click.echo(
            f"(s: {serie.num_seasons} ep: {serie.num_episodes}) : stopped at ({serie.stopped_at[0]}, {serie.stopped_at[1]})\n"
            f"TAGS: {', '.join(serie.tags)}\n"
            f"STATUS: {"CAUGHTUP" if serie.status == Status.CAUGHT_UP else "WATCHING" if serie.status == Status.IN_PROGRESS else "NOT STARTED"}\n"
        )
        choice = click.prompt(
            "[remove] [add-tag <tag>] [remove-tag <tag>] [set-stopped-at <s> <ep>] [back]",
            default="back", show_default=False,
        ).split()

        if not choice or choice[0] == "back":
            return

        action, *rest = choice

        if action == "remove":
            profile.remove_series(serie.id)
            click.echo(f"Removed {serie.name}")
            return  # object no longer exists, so leave the loop
        elif action == "add-tag" and rest:
            serie.add_tag(rest[0])
            click.echo(f"Tagged {serie.name} with {rest[0]}")
        elif action == "remove-tag" and rest:
            serie.remove_tag(rest[0])
            click.echo(f"Removed tag {rest[0]}")
        elif action == "set-stopped-at" and rest:
            serie.set_stoppped_at([rest[0], rest[1]])
            click.echo(f"Updated stopped_at to {rest[0]} {rest[1]}")
        elif action == "caught-up":
            serie.all_caught_up()
        elif action == "reset":
            serie.reset()
        else:
            click.echo("Unrecognized action")



if __name__ == "__main__":
    main()