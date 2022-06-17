import json
import pathlib
from datetime import datetime
from typing import Dict, List

import dash
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from dash import ALL, dcc, html
from dash.dependencies import Input, Output, State
from pcgsepy.config import BIN_POP_SIZE, CS_MAX_AGE, N_GENS_ALLOWED
from pcgsepy.evo.fitness import (Fitness, box_filling_fitness,
                                 func_blocks_fitness, mame_fitness,
                                 mami_fitness)
from pcgsepy.evo.genops import expander
from pcgsepy.hullbuilder import HullBuilder
from pcgsepy.lsystem.solution import CandidateSolution
from pcgsepy.mapelites.behaviors import (BehaviorCharacterization, avg_ma,
                                         mame, mami, symmetry)
from pcgsepy.mapelites.emitters import *
from pcgsepy.mapelites.emitters import (ContextualBanditEmitter,
                                        HumanPrefMatrixEmitter, RandomEmitter)
from pcgsepy.mapelites.map import get_structure
from pcgsepy.setup_utils import get_default_lsystem

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

hull_builder = HullBuilder(erosion_type='bin',
                           apply_erosion=True,
                           apply_smoothing=False)

feasible_fitnesses = [
    #     Fitness(name='BoundingBox',
    #             f=bounding_box_fitness,
    #             bounds=(0, 1)),
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
    BehaviorCharacterization(name='Symmetry',
                             func=symmetry,
                             bounds=(0, 1))
]

behavior_descriptors_names = [x.name for x in behavior_descriptors]


block_to_colour = {
    # colours from https://developer.mozilla.org/en-US/docs/Web/CSS/color_value
    'LargeBlockArmorCorner': '#778899',
    'LargeBlockArmorSlope': '#778899',
    'LargeBlockArmorCornerInv': '#778899',
    'LargeBlockArmorBlock': '#778899',
    'LargeBlockGyro': '#2f4f4f',
    'LargeBlockSmallGenerator': '#ffa07a',
    'LargeBlockSmallContainer': '#008b8b',
    'OpenCockpitLarge': '#32cd32',
    'LargeBlockSmallThrust': '#ff8c00',
    'SmallLight': '#fffaf0',
    'Window1x1Slope': '#fffff0',
    'Window1x1Flat': '#fffff0',
    'LargeBlockLight_1corner': '#fffaf0'
}

def _get_colour_mapping(block_types: List[str]) -> Dict[str, str]:
    colour_map = {}
    for block_type in block_types:
        c = block_to_colour.get(block_type, '#ff0000')
        if block_type not in colour_map.keys():
            colour_map[block_type] = c
    return colour_map


app = dash.Dash(__name__,
                title='Spasceships comparator',
                external_stylesheets=[
                    'https://codepen.io/chriddyp/pen/bWLwgP.css'],
                update_title=None)

def set_app_layout(spaceship: str,
                   ref_spaceships: Dict[str, float]):
    description_str, help_str = '', ''
    
    curr_dir = pathlib.Path(__file__).parent.resolve()
    
    with open(curr_dir.joinpath('assets/description.md'), 'r') as f:
        description_str = f.read()
    with open(curr_dir.joinpath('assets/help.md'), 'r') as f:
        help_str = f.read()
    
    app.layout = html.Div(children=[
        # HEADER
        html.Div(children=[
            html.H1(children='🚀Space Engineers🚀 Spaceships comparator',
                    className='title'),
            dcc.Markdown(children=description_str,
                         className='page-description'),
        ],
            className='header'),
        html.Br(),
        # BODY
        html.Div(children=[
            
            # content plots
            html.Div(children=[
                
                # my spaceship
                html.Div(children=[
                    # title
                    html.Div(children=[
                        html.H1(children='My spaceship',
                                style={'text-align': 'center'})
                        ]),
                    html.Br(),
                    # spaceship content display + properties
                    # CONTENT PLOT
                        html.Div(children=[
                            dcc.Graph(id="my-spaceship-content",
                                    figure=go.Figure(data=[])),
                        ],
                            className='content-div',
                            style={'width': '80%'}),
                        html.Div(children=[
                            html.H6('Content properties',
                                    className='section-title'),
                            html.Div(children=[],
                                    id='my-spaceship-properties'),
                            ],
                                className='properties-div',
                                style={'width': '20%'}),
                    ],
                         style={'width': '50%'}),
                # ref spaceship
                html.Div(children=[
                    # title
                    html.Div(children=[
                        html.H1(children=f'Spaceship 1 / {len(ref_spaceships)}',
                                id='ref-spaceship-current',
                                style={'text-align': 'center'})
                        ]),
                    html.Br(),
                    # spaceship content display + properties
                    # CONTENT PLOT
                        html.Div(children=[
                            dcc.Graph(id="ref-spaceship-content",
                                    figure=go.Figure(data=[])),
                        ],
                            className='content-div',
                            style={'width': '80%'}),
                        html.Div(children=[
                            html.H6('Content properties',
                                    className='section-title'),
                            html.Div(children=[],
                                    id='ref-spaceship-properties'),
                            ],
                                className='properties-div',
                                style={'width': '20%'}),
                    ],
                         style={'width': '50%'}),
                
            ],
                     style={'display': 'flex'}),
            
            html.Br(),
            
            # controls
            html.Div(children=[
                # slider
                html.Div(children=[
                    dcc.Slider(-3, 3, 0.5,
                            value=0,
                            id='value-slider',
                            marks=None,
                            tooltip={"placement": "bottom",
                                     "always_visible": True}),
                    ],
                        style={'width': '60%', 'margin': '0 auto'}),
                html.Br(),
                # prev/next and save buttons
                html.Div(children=[
                    html.Div(children=[
                        html.Button('<',
                                    id='prev-btn',
                                    className='button'),
                        html.Button('>',
                                    id='next-btn',
                                    className='button')
                        ],
                             style={'display': 'flex'}),
                    html.Br(),
                    html.Div(children=[
                        html.Button('SAVE',
                                id='save-btn',
                                disabled=False,
                                className='button'),
                        dcc.Download(id='download-values')
                        ],
                             style={'display': 'flex'})
                    ],
                         style={'width': '20%', 'display': 'flex', 'flex-direction': 'column', 'margin': '0 auto'})
            ],
                     style={'width': '100%', 'display': 'flex', 'flex-direction': 'column', 'justify-content': 'center'})
            ]),
        html.Br(),
        # FOOTER
        html.Div(children=[
            html.H6(children='Help',
                    className='section-title'),
            dcc.Markdown(help_str,
                         className='page-description')
        ],
            className='footer'),
        dcc.Store(id='my-spaceship',
                  data=json.dumps(spaceship)),
        dcc.Store(id='ref-spaceships',
                  data=json.dumps(ref_spaceships)),
        dcc.Store(id='current-idx',
                  data=0),
        dcc.Store(id='values',
                  data=','.join(['0' for _ in range(len(ref_spaceships))]))
    ])


@app.callback(
    Output("download-values", "data"),
    Input("save-btn", "n_clicks"),
    State('values', 'data'),
    State('ref-spaceships', 'data'),
    prevent_initial_call=True,
)
def download_values(n_clicks,
                    values,
                    spaceships):
    spaceships = json.loads(spaceships)
    values = [float(x) for x in values.split(',')]
    t = datetime.now().strftime("%Y%m%d%H%M%S")
    fname = f'{t}'
    content = {k:v for k, v in zip(spaceships, values)}
    return dict(content=json.dumps(content), filename=f'{fname}.log')


def get_content_plot(spaceship: CandidateSolution) -> go.Figure:
    ll_spaceship = lsystem.hl_to_ll(spaceship)
    spaceship.ll_string = ll_spaceship.string
    spaceship.set_content(get_structure(string=spaceship.ll_string,
                                                extra_args={
                                                    'alphabet': lsystem.ll_solver.atoms_alphabet
                                                    }))
    # create content plot...
    hull_builder.add_external_hull(structure=spaceship.content)
    content = spaceship.content.as_grid_array()
    arr = np.nonzero(content)
    x, y, z = arr
    cs = [content[i, j, k] for i, j, k in zip(x, y, z)]
    ss = [spaceship.content._clean_label(spaceship.content.ks[v - 1]) for v in cs]
    fig = px.scatter_3d(x=x,
                        y=y,
                        z=z,
                        color=ss,
                        color_discrete_map=_get_colour_mapping(ss),
                        labels={
                            'x': 'x',
                            'y': 'y',
                            'z': 'z',
                            'color': 'Block type'
                        },
                        title=f'{spaceship.string}')
    fig.update_layout(scene=dict(aspectmode='data'),
                      paper_bgcolor='rgba(0,0,0,0)',
                      plot_bgcolor='rgba(0,0,0,0)')
    return fig


def get_spaceship_properties(spaceship: CandidateSolution) -> Dict[str, Any]:
    spaceship_properties = [
        dcc.Markdown(children=f'**Size**: {spaceship.content.as_grid_array().shape}',
                     className='properties-text'),
        dcc.Markdown(children=f'**Number of blocks**: {spaceship.n_blocks}',
                     className='properties-text')        
    ]
    for bc in behavior_descriptors:
        spaceship_properties.append(dcc.Markdown(children=f'**{bc.name}**: {np.round(bc(spaceship), 4)}',
                                                 className='properties-text'))
    return spaceship_properties


@app.callback(Output('current-idx', 'data'),
              Output('values', 'data'),
              Output('ref-spaceship-current', 'children'),
              Output('ref-spaceship-content', 'figure'),
              Output('ref-spaceship-properties', 'children'),
              Output('my-spaceship-content', 'figure'),
              Output('my-spaceship-properties', 'children'),
              Output('value-slider', 'value'),
              
              Input('value-slider', 'value'),
              Input('prev-btn', 'n_clicks'),
              Input('next-btn', 'n_clicks'),
              
              State('my-spaceship', 'data'),
              State('ref-spaceships', 'data'),
              State('current-idx', 'data'),
              State('values', 'data'))
def general_callback(slider_value, prev_n_clicks, next_n_clicks,
                     my_spaceship, ref_spaceships, current_idx, values):
    ref_spaceships = json.loads(ref_spaceships)
    my_spaceship = json.loads(my_spaceship)
    current_idx = int(current_idx)
    values = [float(x) for x in values.split(',')]
    
    ctx = dash.callback_context

    if not ctx.triggered:
        event_trig = None
    else:
        event_trig = ctx.triggered[0]['prop_id'].split('.')[0]

    if event_trig == 'prev-btn':
        current_idx -= 1
        current_idx = max(0, current_idx)
    elif event_trig == 'next-btn':
        current_idx += 1
        current_idx = min(len(values) - 1, current_idx)
    elif event_trig is not None and 'value-slider' in event_trig:
        values[current_idx] = slider_value
    
    my_spaceship = CandidateSolution(string=my_spaceship)
    my_spaceship_plot = get_content_plot(spaceship=my_spaceship)
    my_spaceship_properties = get_spaceship_properties(spaceship=my_spaceship)
    
    current_spaceship = CandidateSolution(string=list(ref_spaceships.keys())[current_idx])
    current_spaceship_plot = get_content_plot(spaceship=current_spaceship)
    current_spaceship_properties = get_spaceship_properties(spaceship=current_spaceship)
    
    
    
    return str(current_idx), ','.join([str(x) for x in values]), f'Spaceship {current_idx + 1} / {len(values)}', current_spaceship_plot, current_spaceship_properties, my_spaceship_plot, my_spaceship_properties, values[current_idx]
