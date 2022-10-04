from datetime import datetime
from enum import Enum, auto
import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from pcgsepy.config import BIN_POP_SIZE, CS_MAX_AGE, MY_EMITTERS
from pcgsepy.mapelites.behaviors import (BehaviorCharacterization, avg_ma,
                                         mame, mami, symmetry)

from pcgsepy.mapelites.map import MAPElites


class Metric:
    def __init__(self,
                 emitters: List[str],
                 exp_n: int,
                 multiple_values: bool = False) -> None:
        self.current_generation: int = 0
        self.multiple_values = multiple_values
        self.history: Dict[int, List[Any]] = {
            self.current_generation: [] if multiple_values else 0
        }
        self.emitter_names: List[str] = [emitters[exp_n]]
    
    def add(self,
            value: Any):
        if self.multiple_values:
            self.history[self.current_generation].append(value)
        else:
            self.history[self.current_generation] += value
    
    def reset(self):
        if self.multiple_values:
            self.history[self.current_generation] = []
        else:
            self.history[self.current_generation] = 0
    
    def new_generation(self,
                       emitters: List[str],
                       exp_n: int):
        self.current_generation += 1
        self.reset()
        self.emitter_names.append(emitters[exp_n])
    
    def get_averages(self) -> List[Any]:
        return [np.mean(l) for l in self.history.values()]


class Semaphore:
    def __init__(self,
                 locked: bool = False) -> None:
        self._is_locked = locked
        self._running = ''
    
    @property
    def is_locked(self) -> bool:
        return self._is_locked
    
    def lock(self,
             name: Optional[str] = ''):
        self._is_locked = True
        self._running = name
    
    def unlock(self):
        self._is_locked = False
        self._running = ''


class DashLoggerHandler(logging.StreamHandler):
    def __init__(self):
        logging.StreamHandler.__init__(self)
        self.queue = []

    def emit(self, record):
        t = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        msg = self.format(record)
        self.queue.append(f'[{t}]\t{msg}')


class AppMode(Enum):
    USERSTUDY = 0
    USER = 1
    DEV = 2


class AppSettings:
    def __init__(self) -> None:
        self.current_mapelites: Optional[MAPElites] = None
        self.exp_n: int = 0
        self.gen_counter: int = 0
        self.hm_callback_props: Dict[str, Any] = {}
        self.my_emitterslist: List[str] = MY_EMITTERS.copy()
        self.behavior_descriptors: List[BehaviorCharacterization] = [
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
        self.rngseed: int = None
        self.selected_bins: List[Tuple[int, int]] = []
        self.step_progress: int = -1
        self.use_custom_colors: bool = True
        self.app_mode: AppMode = None

    def initialize(self,
                   mapelites: MAPElites,
                   dev_mode: bool = False):
        self.current_mapelites = mapelites
        self.app_mode = AppMode.DEV if dev_mode else self.app_mode
        self.hm_callback_props['pop'] = {
            'Feasible': 'feasible',
            'Infeasible': 'infeasible'
        }
        self.hm_callback_props['metric'] = {
            'Fitness': {
                'name': 'fitness',
                'zmax': {
                    'feasible': sum([x.weight * x.bounds[1] for x in self.current_mapelites.feasible_fitnesses]) + self.current_mapelites.nsc,
                    'infeasible': 1.
                },
                'colorscale': 'Inferno'
            },
            'Age':  {
                'name': 'age',
                'zmax': {
                    'feasible': CS_MAX_AGE,
                    'infeasible': CS_MAX_AGE
                },
                'colorscale': 'Greys'
            },
            'Coverage': {
                'name': 'size',
                'zmax': {
                    'feasible': BIN_POP_SIZE,
                    'infeasible': BIN_POP_SIZE
                },
                'colorscale': 'Hot'
            }
        }
        self.hm_callback_props['method'] = {
            'Population': True,
            'Elite': False
        }