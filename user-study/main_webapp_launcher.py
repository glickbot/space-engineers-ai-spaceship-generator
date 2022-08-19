import logging
import os
import sys

from waitress import serve

if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    os.chdir(sys._MEIPASS)

import argparse
import random
import webbrowser

from pcgsepy.common.jsonifier import json_loads
from pcgsepy.evo.fitness import (Fitness, box_filling_fitness,
                                 func_blocks_fitness, mame_fitness,
                                 mami_fitness)
from pcgsepy.evo.genops import expander
from pcgsepy.guis.main_webapp.webapp import (app, set_app_layout,
                                             set_callback_props)
from pcgsepy.mapelites.behaviors import (BehaviorCharacterization, avg_ma,
                                         mame, mami, symmetry)
from pcgsepy.setup_utils import get_default_lsystem, setup_matplotlib
from pcgsepy.mapelites.buffer import Buffer, mean_merge
from pcgsepy.mapelites.map import MAPElites
from pcgsepy.mapelites.emitters import ContextualBanditEmitter
from pcgsepy.nn.estimators import MLPEstimator


parser = argparse.ArgumentParser()
parser.add_argument("--mapelites_file", help="Location of the MAP-Elites object",
                    type=str, default=None)
parser.add_argument("--dev_mode", help="Launch the webapp in developer mode",
                    action='store_true')
parser.add_argument("--debug", help="Launch the webapp in debug mode",
                    action='store_true')
parser.add_argument("--emitter", help="Specify the emitter type",
                    type=str, choices=['random', 'preference-matrix', 'contextual-bandit'], default='random')
parser.add_argument("--host", help="Specify host address",
                    type=str, default='127.0.0.1')
parser.add_argument("--port", help="Specify port",
                    type=int, default=8050)
parser.add_argument("--use_reloader", help="Use reloader (set to True when using Jupyter Notebooks)",
                    action='store_false')

args = parser.parse_args()

logging.getLogger('werkzeug').setLevel(logging.ERROR)

setup_matplotlib(larger_fonts=False)

used_ll_blocks = [
    'MyObjectBuilder_CubeBlock_LargeBlockArmorCornerInv',
    'MyObjectBuilder_CubeBlock_LargeBlockArmorCorner',
    'MyObjectBuilder_CubeBlock_LargeBlockArmorSlope',
    'MyObjectBuilder_CubeBlock_LargeBlockArmorBlock',
    'MyObjectBuilder_Gyro_LargeBlockGyro',
    'MyObjectBuilder_Reactor_LargeBlockSmallGenerator',
    'MyObjectBuilder_CargoContainer_LargeBlockSmallContainer',
    'MyObjectBuilder_Cockpit_OpenCockpitLarge',
    'MyObjectBuilder_Thrust_LargeBlockSmallThrust',
    'MyObjectBuilder_InteriorLight_SmallLight',
    'MyObjectBuilder_CubeBlock_Window1x1Slope',
    'MyObjectBuilder_CubeBlock_Window1x1Flat',
    'MyObjectBuilder_InteriorLight_LargeBlockLight_1corner'
]

lsystem = get_default_lsystem(used_ll_blocks=used_ll_blocks)

expander.initialize(rules=lsystem.hl_solver.parser.rules)

feasible_fitnesses = [
    Fitness(name='BoxFilling',
            f=box_filling_fitness,
            bounds=(0, 1)),
    Fitness(name='FuncionalBlocks',
            f=func_blocks_fitness,
            bounds=(0, 1)),
    Fitness(name='MajorMediumProportions',
            f=mame_fitness,
            bounds=(0, 1)),
    Fitness(name='MajorMinimumProportions',
            f=mami_fitness,
            bounds=(0, 1))
]

behavior_descriptors = [
    BehaviorCharacterization(name='Major axis / Medium axis',
                             func=mame,
                             bounds=(0, 10)),
    BehaviorCharacterization(name='Major axis / Smallest axis',
                             func=mami,
                             bounds=(0, 20)),
    BehaviorCharacterization(name='Average Proportions',
                             func=avg_ma,
                             bounds=(0, 20)),
    BehaviorCharacterization(name='Symmetry',
                             func=symmetry,
                             bounds=(0, 1))
]

behavior_descriptors_names = [x.name for x in behavior_descriptors]

available_mapelites = ['mapelites_random.json',
                       'mapelites_prefmatrix.json', 'mapelites_contbandit.json']

# if args.mapelites_file:
#     with open(args.mapelites_file, 'r') as f:
#         mapelites = json_loads(f.read())
# else:
#     mapelites_file = random.choice(available_mapelites)
#     with open(mapelites_file, 'r') as f:
#         mapelites = json_loads(f.read())

buffer = Buffer(merge_method=mean_merge)
mapelites = MAPElites(lsystem=lsystem,
                      feasible_fitnesses=feasible_fitnesses,
                      estimator=MLPEstimator(xshape=len(feasible_fitnesses),
                                             yshape=1),
                      buffer=buffer,
                      behavior_descriptors=behavior_descriptors,
                      n_bins=(8,8),
                      emitter=ContextualBanditEmitter())
# mapelites.generate_initial_populations()

set_callback_props(mapelites=mapelites)

set_app_layout(behavior_descriptors_names=behavior_descriptors_names,
               mapelites=mapelites,
               dev_mode=args.dev_mode)

webapp_url = f'http://{args.host}:{args.port}/'
print(f'Serving webapp on http://{args.host}:{args.port}/...')
webbrowser.open_new(webapp_url)

serve(app.server,
      threads=16,
      host=args.host,
      port=args.port)