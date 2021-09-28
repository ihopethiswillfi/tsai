# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/201_wandb.ipynb (unless otherwise specified).

__all__ = ['run_sweep', 'get_wandb_agent']

# Cell
from fastcore.script import *
from .imports import *

@call_parse
def run_sweep(path:      Param('Path to file with the sweep script file', str) = None,
              entity:    Param("username or team name where you're sending runs", str) = None,
              project:   Param("The name of the project where you're sending the new run.", str) = None,
              count:     Param('Number of runs to execute', int) = None,
              sweep_id:  Param('Sweep ID. This option omits `sweep`', str) = None,
              launch:    Param("Launch wanbd agent.", store_false) = True,
              relogin:   Param('Relogin to wandb.', store_true) = False,
              login_key: Param('Login key for wandb', str) = None,
              ):

    try: import wandb
    except ImportError: raise ImportError('You need to install wandb to run sweeps!')

    # Login to W&B
    if relogin: wandb.login(relogin=True)
    elif login_key: wandb.login(key=login_key)

    # Sweep id
    mod = import_file_as_module(path)
    if not sweep_id:
        sweep_id = wandb.sweep(mod.sweep, entity=entity, project=project)

    # Agent
    print(f"\nwandb agent {os.environ['WANDB_ENTITY']}/{os.environ['WANDB_PROJECT']}/{sweep_id}\n")
    if launch: wandb.agent(sweep_id, function=mod.train, count=count)

# Cell
def get_wandb_agent(sweep, entity=None, project=None, count=None):
    try: import wandb
    except ImportError: raise ImportError('You need to install wandb to run sweeps!')
    sweep_id = wandb.sweep(sweep, entity=entity, project=project)
    print(f"\nwandb agent {os.environ['WANDB_ENTITY']}/{os.environ['WANDB_PROJECT']}/{sweep_id}\n")