# Import packages
import datetime
from sqlite3.dbapi2 import paramstyle
from sys import maxsize
from functools import lru_cache

import numpy as np
from dash import Dash, html, dcc, callback, Output, Input, State
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import utils
from utils import ERROR_TYPE, ERROR_RETURNED
import re
import plotly.express as px
from github import Auth
from github import Github
import os
import base64
from flask import Flask

scriptPath=os.path.dirname(os.path.realpath(__file__))

# Initialize the app - incorporate a Dash Bootstrap theme
external_stylesheets = [dbc.themes.SOLAR]
server=Flask(__name__)
app = Dash(__name__, external_stylesheets=external_stylesheets,server=server)

# Load global datas
releaseData, commitData, sortedReleaseIdx, sortedCommitIdx = utils.loadAllResults(os.path.join(scriptPath,"../old_results"))

#Create Default variables
defaultGitDataType = 'releases'
defaultCommitSince = '2000-12-31'
defaultCommitInterval = 1
defaultIds = utils.computeCommitListIdInDataList(releaseData,sortedReleaseIdx,datetime.datetime.fromisoformat(defaultCommitSince),defaultCommitInterval)
defaultSceneNames = utils.getUniqueSetOfScenes(releaseData,defaultIds)
defaultSceneNames.sort()
defaultLabels = utils.getUniqueSetOfLabels(releaseData,defaultIds,defaultSceneNames[0])
defaultLabels.sort()
defaultDropDownLabels = [{"label" : name, "value": name} for name in defaultSceneNames]


# Function cache
g_timer_label_color_map = []
g_scene_label_color_map = []
g_overviewLabel = 'TimeStep'
g_maxCache = 10
g_commitInfoCache = 50

# Github handler
GithubToken = os.environ.get('RO_GITHUB_TOKEN')
if(GithubToken is None):
    print("ERROR : Please provide a read only github token through the environment variable RO_GITHUB_TOKEN")
    exit(1)
auth = Auth.Token(GithubToken)
git = Github(auth=auth)
sofaRepo = git.get_repo("sofa-framework/sofa")

### CSS styles
#### FIRST ROW
TITLE_STYLE = {
    "padding":"2rem 0rem 1rem 0rem"
}
LOGO_STYLE = {
    "width":"100px",
    "top":"10px",
    "left":"10px",
    "white-space": "nowrap",
    "position":"absolute"
}

#### SECOND ROW
SECOND_ROW_STYLE = {
    "padding":"0rem 1rem 0rem 1rem",
    "centered": True
}

#### THIRD_ROW
LABEL_CHECKLIST_STYLE={
    "max-height": "120px",
    "height": "100%",
    "overflow":"scroll",
    "overflow-x":"hidden",
    "padding":"0.6rem 1rem 1rem 1rem"
}

GRAPH_STYLE = {
    "padding": "0rem 0rem 0rem 1rem",
    "max-height": "900px"
}

COMMIT_INFO_STYLE = {
    "padding": "0rem 1rem",
    "height": "100%",
     "max-height": "900px",
}

CARD_BODY_STYLE = {

    "overflow":"scroll",
    "overflow-x":"hidden",
    "height": "100%",
    "max-height": "820px",
}

FULL_THIRD_ROW_STYLE = {
    "max-height": "920px",
    "height": "100%"
}


# Plots panel tabs
tab_overview_graph = dbc.Card([
        dbc.Row([
            dbc.Col(dbc.Checklist(options=defaultSceneNames,
                          value=defaultSceneNames,
                          inline=True,
                          id='scenes_names')),
            dbc.Col([dbc.Checklist(options=[{"label":"Select all","value":1}],
                                  value=[1],
                                  inline=True,
                                  id='select_all_scenes',
                                  switch=True),
            dbc.Checklist(options=[{"label":"Log scale","value":1}],
                           value=[],
                           inline=True,
                           id='log_scale_overview',
                           switch=True)
                ], width= 2)

        ],
            style=LABEL_CHECKLIST_STYLE
        ),
        dcc.Graph(figure={}, id='PlotOverview'),
    ],


    className="mt-3",
)

tab_specific_graph = dbc.Card(
    [dbc.Row([
        dbc.Col(dbc.Checklist(options=defaultLabels,
                              value=[g_overviewLabel],
                              inline=True,
                              id='labels',
                              ),
            ),

        dbc.Col([
            dbc.Checklist(options=[{"label":"Select all","value":1}],
                          value=[],
                          inline=True,
                          id='select_all_labels',
                          switch=True,
                          style={"padding": "0rem 0rem 0rem 0rem"}),
            dbc.Checklist(options=[{"label":"Log scale","value":1}],
                          value=[],
                          inline=True,
                          id='log_scale_timer',

                          switch=True),
            ],
            width=2    ),
        dbc.Col([dbc.Label("Scene name"),
            dbc.Select(defaultDropDownLabels,
                       defaultDropDownLabels[0]["value"],
                       id='sceneName'
                       ),
            ],
            width= 3)

    ],
    style=LABEL_CHECKLIST_STYLE), #
    dcc.Graph(figure={}, id='PlotTimerSpecific')],
    className="mt-3",
)


# Right info panel tabs
tab_commit_info = dbc.Card(
    dbc.CardBody(
        [html.P(f"No commit selected")],
        id='commit-info',
        style=CARD_BODY_STYLE
    ),
    className="mt-3",
)

tab_hard_info = dbc.Card(
    dbc.CardBody(
        [html.P(f"No commit selected")],
    id='hard-info',
    style=CARD_BODY_STYLE
    ),
    className="mt-3",
)


logo_base64 = base64.b64encode(open(os.path.join(scriptPath,"SOFA_S_carre_bordure.png"), 'rb').read()).decode('ascii')


# App layout
app.layout = dbc.Container([

    html.A(html.Img(src='data:image/png;base64,{}'.format(logo_base64),style=LOGO_STYLE),href="https://www.sofa-framework.org/",target="_blank"),
    dbc.Row([
        html.Div(html.B('SOFA Performance testing dashboard'), className="text-primary text-bold text-center fs-1",style=TITLE_STYLE)
    ]),
    html.Hr(),
    dbc.Row([
        dbc.Col([
            dbc.Label("Commit type"),
            dbc.Select([
                    {"label": "releases", "value": "releases"},
                    {"label": "master", "value": "master"}
                ],
                defaultGitDataType,
                id='git-data-type'
            )
            ],
            width=2
        ),

        dbc.Col([
                dbc.Label("Commit since"),
                dbc.Input(id='commit-since', value=defaultCommitSince, placeholder="Commit since",type='text')
            ],
            width=2
        ),
        dbc.Col([
                dbc.Label("Commit interval"),
                dbc.Input(id='commit-interval', value=defaultCommitInterval, type='number', min=1, step=1),
            ],
            width=2
        )
        ],
        style=SECOND_ROW_STYLE
    ),
    html.Hr(),
    dbc.Row([
        dbc.Col([
            html.Div([
                dbc.Tabs([
                    dbc.Tab(tab_overview_graph, label="Timestep overview"),
                    dbc.Tab(tab_specific_graph, label="Timers"),
                    ]
                )
                ],
                style=GRAPH_STYLE
            )
            ],
            width=8
        ),
        dbc.Col([
            html.Div(
            [
            dbc.Tabs(
                [
                    dbc.Tab(tab_commit_info, label="Commit info"),
                    dbc.Tab(tab_hard_info, label="Hardware info"),
                ]
            )
            ],
            style=COMMIT_INFO_STYLE)
        ], width=4),

        ], align=True
         , style=FULL_THIRD_ROW_STYLE),
        html.Hr(),
], fluid=True)



##### COMMON CALLBACK AND METHODS #####

@lru_cache(maxsize = g_maxCache)
def get_ids_for_callback(git_data_type,commit_since,commit_interval):
    global releaseData,sortedReleaseIdx,commitData,sortedCommitIdx

    try:
        commit_since_date = datetime.datetime.fromisoformat(commit_since)
    except(ValueError):
        print("Date is not in iso format : 'YYYY-MM-DD HH:MM:SS' time is optional" )
        return ERROR_RETURNED

    if(git_data_type=="releases"):
        outputIds = utils.computeCommitListIdInDataList(releaseData,sortedReleaseIdx,commit_since_date,commit_interval)
    else:
        outputIds = utils.computeCommitListIdInDataList(commitData,sortedCommitIdx,commit_since_date,commit_interval)

    return outputIds

@lru_cache(maxsize = g_maxCache)
def get_scenes_names_for_callback(git_data_type,commit_since,commit_interval):
    global releaseData,sortedReleaseIdx,commitData,sortedCommitIdx

    ids = get_ids_for_callback(git_data_type,commit_since,commit_interval)

    if(isinstance(ids,ERROR_TYPE)):
        return ERROR_RETURNED

    if(git_data_type=="releases"):
        raw_names = utils.getUniqueSetOfScenes(releaseData,ids)
    else:
        raw_names = utils.getUniqueSetOfScenes(commitData,ids)

    raw_names.sort()


    return raw_names


def getGlobalTimerColor(label):
    global g_timer_label_color_map

    try:
        idx = g_timer_label_color_map.index(label)
    except(ValueError):
        g_timer_label_color_map.append(label)
        idx = len(g_timer_label_color_map) -1

    return px.colors.qualitative.Alphabet[idx%len(px.colors.qualitative.Alphabet)]

def getGlobalSceneColor(label):
    global g_scene_label_color_map

    try:
        idx = g_scene_label_color_map.index(label)
    except(ValueError):
        g_scene_label_color_map.append(label)
        idx = len(g_scene_label_color_map) -1

    return px.colors.qualitative.Alphabet[idx%len(px.colors.qualitative.Alphabet)]

@lru_cache(maxsize = g_commitInfoCache)
def get_commit_info_data_for_callback(commitHash,sceneName,timerName):
    global releaseData, commitData, sortedReleaseIdx, sortedCommitIdx

    isRelease = re.match("v[0-9]{2}.[0-9]{2}",commitHash) is not None
    commit = sofaRepo.get_commit(commitHash)
    commitRawData = commit.raw_data

    try:
        if(isRelease):
            releaseId = utils.findCommitId(releaseData,commitHash)

            sceneIndex = releaseData[releaseId].sceneNames.index(sceneName)
            cpuIndex = releaseData[releaseId].timerNames.index("CPUUsage")
            cpuIndexInSamples = releaseData[releaseId].sceneTimers[sceneIndex].index(cpuIndex)
            cpuData = releaseData[releaseId].sceneSamples[sceneIndex][cpuIndexInSamples]
            timerIndex = releaseData[releaseId].timerNames.index(timerName)
            timerIndexInSamples = releaseData[releaseId].sceneTimers[sceneIndex].index(timerIndex)
            timerCardinality = releaseData[releaseId].sceneSamples[sceneIndex][timerIndexInSamples].cardinality
        else:
            commitId = utils.findCommitId(commitData,commit.sha)

            sceneIndex = commitData[commitId].sceneNames.index(sceneName)
            cpuIndex = commitData[commitId].timerNames.index("CPUUsage")
            cpuIndexInSamples = commitData[commitId].sceneTimers[sceneIndex].index(cpuIndex)
            cpuData = commitData[commitId].sceneSamples[sceneIndex][cpuIndexInSamples]

            timerIndex = commitData[commitId].timerNames.index(timerName)
            timerIndexInSamples = commitData[commitId].sceneTimers[sceneIndex].index(timerIndex)
            timerCardinality = commitData[commitId].sceneSamples[sceneIndex][timerIndexInSamples].cardinality

        CpuString = f"CPU Usage : {cpuData.meanstd[0]:.2f}% ± {2*cpuData.meanstd[1]:.2f} (5% confidence)"
        if((cpuData.meanstd[0] + 2*cpuData.meanstd[1]) <= 5):
            CpuColor = '#21b239'
        elif((cpuData.meanstd[0] + 2*cpuData.meanstd[1]) <= 10):
            CpuColor = "#eb9a2d"
        else:
            CpuColor = "#ff2222"


    except(ValueError):
        CpuString = "CPU Usage : no stat found"
        CpuColor = "#BBBBBB"

    currCommitInfo = [
        html.P(["Commit hash : ",html.B(f"{commitHash}")], className="text-secondary"),
        html.P(["Commit message : ",html.B(f"{commitRawData["commit"]["message"].split('\n')[0]}")], className="text-secondary"),
        html.P(f"Date : {commitRawData["commit"]["author"]["date"].replace('T',' ').replace('Z',' ')}"),
        html.P([f"Author : {commitRawData["commit"]["author"]["name"]} "]),
        html.P([f"Link : ", html.A(f"{commitRawData["html_url"]}",href=commitRawData["html_url"])]),
        html.Hr(),
        html.P([ html.P(f"Numer of samples : {timerCardinality}"),  html.P(CpuString,style={'color':CpuColor})]),
    ]

    return currCommitInfo

@lru_cache(maxsize = g_maxCache)
def get_hard_info_data_for_callback(commitHash):
    global releaseData, commitData, sortedReleaseIdx, sortedCommitIdx


    isRelease = (re.match("v[0-9]{2}.[0-9]{2}",commitHash) is not None) or (commitHash == "master")
    commit = sofaRepo.get_commit(commitHash)

    try:
        if(isRelease):
            releaseId = utils.findCommitId(releaseData,commitHash)
            hardInfo = releaseData[releaseId].hardInfo
        else:
            commitId = utils.findCommitId(commitData,commit.sha)
            hardInfo = commitData[commitId].hardInfo
    except(ValueError):
        hardInfo = "Hardware info : not found"


    # Generate HTML struct from hard info file. This works only if hardinfo file has parts titles
    # starting with a char at pose 0 and part content having a space at beginning of line
    retList = []
    Paragraph = []
    for infoLine in hardInfo:
        if(len(infoLine) > 0):
            if(infoLine[0] != " "):
                if(len(Paragraph) > 0 ):
                    retList.append(html.P(Paragraph,style={"margin-left":"25px"}))
                    Paragraph = []
                retList.append(html.H5(infoLine))
            else:
                Paragraph.append(infoLine)
                Paragraph.append(html.Br())
    if(len(Paragraph) > 0 ):
        retList.append(html.P(Paragraph,style={"margin-left":"25px"}))

    return retList


##### OVERVIEW GRAPH #####

@callback(

    Output(component_id='scenes_names', component_property='options'),
    State(component_id='scenes_names', component_property='options'),
    Input(component_id='git-data-type', component_property='value'),
    Input(component_id='commit-since', component_property='value'),
    Input(component_id='commit-interval', component_property='value')
)
def update_scene_names_for_timers(currSceneNames,git_data_type,commit_since,commit_interval):
    raw_names = get_scenes_names_for_callback(git_data_type,commit_since,commit_interval)
    if(isinstance(raw_names,ERROR_TYPE)):
        return currSceneNames
    else:
        return raw_names


@callback(

    Output(component_id='scenes_names', component_property='value'),
    State(component_id='scenes_names', component_property='options'),
    Input(component_id='select_all_scenes', component_property='value'),
)
def update_scene_checked_for_timers(sceneNames,selectAll):
    if(len(selectAll)>0):
        return sceneNames
    else:
        return []


@callback(
    Output(component_id='PlotOverview', component_property='figure'),
    State(component_id='PlotOverview', component_property='figure'),
    Input(component_id='git-data-type', component_property='value'),
    Input(component_id='commit-since', component_property='value'),
    Input(component_id='commit-interval', component_property='value'),
    Input(component_id='scenes_names', component_property='value'),
    Input(component_id='log_scale_overview', component_property='value')
)
def update_overview_graph(currFigure,git_data_type,commit_since,commit_interval, sceneNames,logScale):
    global releaseData, commitData, sortedReleaseIdx, sortedCommitIdx, currLabels, g_overviewLabel

    ids = get_ids_for_callback(git_data_type,commit_since,commit_interval)
    if(isinstance(ids,ERROR_TYPE)):
        return currFigure

    sceneNames.sort()

    fig = go.Figure()
    globalLabels = []
    for scene in sceneNames:
        if(git_data_type=="releases"):
            xLabelList , DataStruct = utils.getDataStructureForGraph(releaseData, ids , scene, [g_overviewLabel], type = "mean" )
        else:
            xLabelList , DataStruct = utils.getDataStructureForGraph(commitData, ids , scene, [g_overviewLabel], type = "mean")

        if(np.size(DataStruct[g_overviewLabel]) != 0):
            for xLabel in xLabelList: #Prepare label list for label reordering (see later)
                if xLabel not in globalLabels:
                    globalLabels.append(xLabel)
            fig.add_trace(go.Scatter(x=xLabelList[g_overviewLabel],
                                     y=DataStruct[g_overviewLabel][0],
                                     error_y=dict(type='data',visible=True,array=DataStruct[g_overviewLabel][1]),
                                     marker_color= getGlobalSceneColor(scene),
                                     name=scene))

    #Reorder labels because it might be reordered because some timers might be missing in the first commits
    orderedGlobalLabels = []
    for i in ids:
        if(git_data_type=="releases"):
            currLabel = releaseData[i].fullHash
        else:
            currLabel = commitData[i].fullHash
        if(len(currLabel)>7):
            currLabel = currLabel[:6]
        if(currLabel in globalLabels):
            orderedGlobalLabels.append(currLabel)

    fig.update_xaxes(categoryorder='array',
                     categoryarray= orderedGlobalLabels)

    #Enale log scale
    if(logScale):
        fig.update_yaxes(type="log")


    if(git_data_type=="releases"):
        xTitle = "Release version"
    else:
        xTitle = "Commit hash"

    fig.update_layout(
        title=dict(
            text='Whole time step execution time',
            x=0.5,
            font=dict(
                size=20
            )
        ),
        yaxis=dict(
            title=dict(
                text='Computation time (ms)')
        ),
        xaxis=dict(
            title=dict(
                text=xTitle)
        ),
        height=725,
        boxmode='group', # group together boxes of the different traces for each value of x
        clickmode='event+select'
    )

    return fig

@callback(
    Output(component_id='commit-info', component_property='children',allow_duplicate=True),
    State(component_id='commit-info', component_property='children'),
    Input(component_id='PlotOverview', component_property='clickData'),
    State(component_id='scenes_names', component_property='value'),
    prevent_initial_call=True)
def display_click_commit_info_data_from_overview(currCommitInfo,clickData,sceneNames):
    if(clickData is not None):
        sceneNames.sort()
        commitName = clickData['points'][0]['x']
        sceneName = sceneNames[clickData['points'][0]['curveNumber']]
        commitInfo = get_commit_info_data_for_callback(commitName,sceneName,g_overviewLabel)

        stats = html.P([html.P([html.B("Scene name : "),sceneName]),
                        html.B("Statistics"),
                        html.P([
                            f"Mean : {clickData['points'][0]['y']:.4f}",html.Br(),
                            f"Std : {clickData['points'][0]['error_y.array']:.4f}"],
                            style={"margin-left":"25px"})])
        output = commitInfo.copy()
        output.insert(-1,stats)

        return output
    else:
        return currCommitInfo


@callback(
    Output(component_id='hard-info', component_property='children',allow_duplicate=True),
    State(component_id='hard-info', component_property='children'),
    Input(component_id='PlotOverview', component_property='clickData'),
    prevent_initial_call=True)
def display_click_hard_info_data_from_overview(currHardInfo,clickData):
    if(clickData is not None):
        commitName = clickData['points'][0]['x']
        return get_hard_info_data_for_callback(commitName)
    else:
        return currHardInfo


##### TIMER GRAPH #####


@callback(

    Output(component_id='labels', component_property='value'),
    State(component_id='labels', component_property='options'),
    Input(component_id='select_all_labels', component_property='value'),
    config_prevent_initial_callbacks=True
)
def update_scene_checked_for_timers(labelNames,selectAll):
    if(len(selectAll)>0):
        return labelNames
    else:
        return []

@callback(
    Output(component_id='labels', component_property='options'),
    State(component_id='labels', component_property='options'),
    Input(component_id='git-data-type', component_property='value'),
    Input(component_id='commit-since', component_property='value'),
    Input(component_id='commit-interval', component_property='value'),
    Input(component_id='sceneName', component_property='value')
)
def update_labels(currLabels,git_data_type,commit_since,commit_interval,sceneName):
    global releaseData, commitData, sortedReleaseIdx, sortedCommitIdx

    ids = get_ids_for_callback(git_data_type,commit_since,commit_interval)
    if(isinstance(ids,ERROR_TYPE)):
        return currLabels

    if(git_data_type=="releases"):
        raw_labels = utils.getUniqueSetOfLabels(releaseData,ids,sceneName)
    else:
        raw_labels = utils.getUniqueSetOfLabels(commitData,ids,sceneName)

    raw_labels.sort()
    if len(raw_labels) == 0:
        return currLabels

    raw_labels.remove("CPUUsage") #Should not be selectable but displayed on the info panel

    return raw_labels

@callback(
    Output(component_id='sceneName', component_property='options'),
    State(component_id='sceneName', component_property='options'),
    Input(component_id='git-data-type', component_property='value'),
    Input(component_id='commit-since', component_property='value'),
    Input(component_id='commit-interval', component_property='value')
)
def update_scene_names_for_timers(currDropdownLabel,git_data_type,commit_since,commit_interval):
    raw_names = get_scenes_names_for_callback(git_data_type,commit_since,commit_interval)

    if(isinstance(raw_names,ERROR_TYPE)):
        return currDropdownLabel
    else:
        return [{"label" : name, "value": name} for name in raw_names]



@callback(
    Output(component_id='PlotTimerSpecific', component_property='figure'),
    State(component_id='PlotTimerSpecific', component_property='figure'),
    Input(component_id='git-data-type', component_property='value'),
    Input(component_id='commit-since', component_property='value'),
    Input(component_id='commit-interval', component_property='value'),
    Input(component_id='labels', component_property='value'),
    Input(component_id='sceneName', component_property='value'),
    Input(component_id='log_scale_timer', component_property='value')
)
def update_timer_graph(currFig,git_data_type,commit_since,commit_interval,labels, sceneName,logScale):
    global releaseData, commitData, sortedReleaseIdx, sortedCommitIdx

    labels.sort()

    ids = get_ids_for_callback(git_data_type,commit_since,commit_interval)

    if(isinstance(ids,ERROR_TYPE)):
        return currFig

    if(git_data_type=="releases"):
        xLabelList, outputStruct = utils.getDataStructureForGraph(releaseData, ids , sceneName, labels, type = "quartiles" )
    else:
        xLabelList, outputStruct = utils.getDataStructureForGraph(commitData, ids , sceneName, labels, type = "quartiles")

    fig = go.Figure()

    globalLabels = []
    for label in xLabelList:
        if(np.size(outputStruct[label]) != 0):
            for xLabel in xLabelList[label]: #Prepare label list for label reordering (see later)
                if xLabel not in globalLabels:
                    globalLabels.append(xLabel)
            fig.add_trace(go.Box(lowerfence=outputStruct[label][0],
                                 q1=outputStruct[label][1],
                                 median=outputStruct[label][2],
                                 q3=outputStruct[label][3],
                                 upperfence=outputStruct[label][4],
                                 x=xLabelList[label],
                                 marker_color= getGlobalTimerColor(label),

                                 name=label))

    #Reorder labels because it might be reordered because some timers might be missing in the first commits
    orderedGlobalLabels = []
    for i in ids:
        if(git_data_type=="releases"):
            currLabel = releaseData[i].fullHash
        else:
            currLabel = commitData[i].fullHash
        if(len(currLabel)>7):
            currLabel = currLabel[:6]
        if(currLabel in globalLabels):
            orderedGlobalLabels.append(currLabel)

    fig.update_xaxes(categoryorder='array',
                     categoryarray= orderedGlobalLabels)

    #Enable logscale
    if(logScale):
        fig.update_yaxes(type="log")

    if(git_data_type=="releases"):
        xTitle = "Release version"
    else:
        xTitle = "Commit hash"

    fig.update_layout(
        title=dict(
            text='Per timer statistics (quartiles)',
            x=0.5,
            font=dict(
                size=20
            )
        ),
        yaxis=dict(
            title=dict(
                text='Computation time (ms)')
        ),
        xaxis=dict(
            title=dict(
                text=xTitle)
        ),
        height=725,
        boxmode='group', # group together boxes of the different traces for each value of x
        clickmode='event+select'
    )

    return fig




@callback(
    Output(component_id='commit-info', component_property='children',allow_duplicate=True),
    State(component_id='commit-info', component_property='children'),
    Input(component_id='PlotTimerSpecific', component_property='clickData'),
    State(component_id='sceneName', component_property='value'),
    State(component_id='labels', component_property='value'),
    prevent_initial_call=True)
def display_click_commit_info_data_from_timer(currCommitInfo,clickData,sceneName,labels):

    if(clickData is not None):
        commitName = clickData['points'][0]['x']
        timerLabel = labels[clickData['points'][0]['curveNumber']]

        print(timerLabel)

        commitInfo = get_commit_info_data_for_callback(commitName,sceneName,timerLabel)
        stats = html.P([html.B("Statistics"),
                        html.P([
                            f"Min : {clickData['points'][0]['lowerfence']:.4f}",html.Br(),
                            f"Q1 : {clickData['points'][0]['q1']:.4f}",html.Br(),
                            f"Median : {clickData['points'][0]['median']:.4f}",html.Br(),
                            f"Q3 : {clickData['points'][0]['q3']:.4f}",html.Br(),
                            f"Max : {clickData['points'][0]['upperfence']:.4f}"],
                            style={"margin-left":"25px"})])
        output = commitInfo.copy()
        output.insert(-1,stats)
        return output
    else:
        return currCommitInfo

@callback(
    Output(component_id='hard-info', component_property='children',allow_duplicate=True),
    State(component_id='hard-info', component_property='children'),
    Input(component_id='PlotTimerSpecific', component_property='clickData'),
    prevent_initial_call=True)
def display_click_hard_info_data(currHardInfo,clickData):

    if(clickData is not None):
        commitName = clickData['points'][0]['x']
        return get_hard_info_data_for_callback(commitName)
    else:
        return currHardInfo



# Run the app
if __name__ == '__main__':
    app.run_server()