from datetime import datetime, timedelta
import requests
import dash
from dash import Dash, dcc, html, Input, Output, callback
import plotly
import json
import pandas as pd
import numpy as np
import plotly.express as px
from ftplib import FTP

# pip install pyorbital
# satellite = Orbital('TERRA')

def createPlot(df):

    Now = datetime.now()
    # Tomorrow = Now + timedelta(hours=24)

    xData = df["t"]
    yData = df["PTot"]

    fig = px.area(x=xData[0:len(xData)-1], y=yData[0:len(yData)-1]/1000)
    fig.update_traces(line_color='orange')
    GraphData = fig.to_html('graph.html')
    PMax = 250.8
    fig.update_yaxes(range=[0, max(200, PMax)])
    fig.update_xaxes(range=[datetime(Now.year, Now.month, Now.day, 0, 0, 0), datetime(Now.year, Now.month, Now.day, 23, 59, 59)])
    fig.update_layout(height=1900, width=1900, paper_bgcolor='lightblue')
    fig.layout.yaxis.title = "Potenza [kW]"
    fig.layout.xaxis.title = ""

    return fig


def aggregateData():

    InvPsKey = ["5297443_1_7_1", "5297443_1_6_1", "5297443_1_5_1", "5297443_1_4_1", "5297443_1_3_1", "5297443_1_2_1", "5297443_1_1_1"]

    Now = datetime.now()
    t0 = datetime(Now.year, Now.month, Now.day, 0, 0, 0)
    dt = timedelta(minutes=5)
    t = t0

    dfFinale = pd.DataFrame()

    for i in range(len(InvPsKey)):

        df = pd.read_csv(InvPsKey[i]+"Powers.csv")

        tSamples = df["t"]
        tSamples = pd.to_datetime(tSamples)
        PSamples = np.array(df["P"])

        t = t0

        tOut = []
        POut = []
        index = 0

        while t <= Now:

            tOut.append(t)
            tSample = tSamples[t == tSamples]

            if len(tSample) == 0:
                A = 2
                POut.append(float('nan'))
            else:
                POut.append(PSamples[index])

            t = t + dt
            index = index + 1

        dfFinale["t"] = tOut
        dfFinale[InvPsKey[i]] = POut

    PTot = []

    for i in range(len(tOut)):
        PTot.append(np.nansum(dfFinale.iloc[i][2:8]))

    dfFinale["PTot"] = PTot

    return dfFinale


def queryData(Plant, token):

    # GTI = queryGTI()

    ps_name = 'Cavarzan'
    ps_id = "5297443"

    InvPsKey = ["5297443_1_7_1", "5297443_1_6_1", "5297443_1_5_1", "5297443_1_4_1", "5297443_1_3_1", "5297443_1_2_1", "5297443_1_1_1"]

    headers = {
        "accept": "application/json",
        "x-access-key": 'dpiixeb8cnn34widwp7ihg5nzfb8eybw',
        "sys_code": '901',
        "Content-Type": "application/json"
    }   # QUESTA LINEA VA CAMBIATA PER MASCHERARE LE CREDENZIALI

    Now = datetime.now()

    DayOnsetLocal = datetime(Now.year, Now.month, Now.day, 0, 0, 0)

    # DayOnsetUTC = DayOnsetLocal
    URL = 'https://gateway.isolarcloud.eu/openapi/getDevicePointMinuteDataList'

    for i in range(len(InvPsKey)): # ciclo sugli inverter
        tLim = DayOnsetLocal + timedelta(hours=3)
        tIn = DayOnsetLocal

        OutPowers = []
        OutTime = []

        while tLim <= Now+timedelta(hours=3):  # ciclo sul tempo

            end_time_stamp = tLim.strftime("%Y%m%d%H%M%S")
            start_time_stamp = tIn.strftime("%Y%m%d%H%M%S")

            param = {

                "appkey": "AAA324AF620903ED6ECCDDEA0B6BC866",
                "ps_id": ps_id,
                "curPage": "1",
                "token": token,
                "size": "10",
                "ps_key_list": InvPsKey,
                "start_time_stamp": start_time_stamp,
                "end_time_stamp": end_time_stamp,
                "points": "p24",

            }

            param = json.dumps(param)
            # headers = json.dumps(headers)

            resp = requests.post(URL, headers=headers, data=param)
            resp = resp.json()

            Powers = resp["result_data"]

            InvPower = Powers[InvPsKey[i]]

            for j in range(len(InvPower[:])):  # ciclo sui samples per estrarre valori

                OutPowers.append(float(InvPower[j]['p24']))
                timeString = InvPower[j]['time_stamp']
                timeStringLocal = datetime.strptime(timeString, "%Y%m%d%H%M%S")
                # timezone2 = pytz.timezone('utc')
                # timezone_date_time_obj = timezone2.localize(timestampUTCButLocal)
                # timeStringLocal = timezone_date_time_obj.astimezone(timezone('Europe/Rome')).replace(tzinfo=None)
                OutTime.append(timeStringLocal)

            tLim = tLim + timedelta(hours=3)
            tIn = tIn + timedelta(hours=3)

        # OutTime = pd.to_datetime(OutTime, format="%d/%m/%Y %H:%M:%S")
        OutTime = np.array(OutTime)
        OutPowers = np.array(OutPowers)

        Data = pd.DataFrame({'t': OutTime, "P": OutPowers})
        Data.to_csv(InvPsKey[i]+"Powers.csv")


def readDataFTP():

    ftp = FTP("192.168.10.211", timeout=120)
    ftp.login('ftpdaticentzilio', 'Sd2PqAS.We8zBK')

    ftp.cwd('/dati/Cavarzan')
    Filename = "CavarzanDailyPlot.csv"
    gFile = open(Filename, "wb")

    ftp.retrbinary("RETR " + Filename, gFile.write)
    gFile.close()

    df = pd.read_csv(Filename)

    return df


def authenticateISC():

    headers = {
        "accept": "application/json",
        "x-access-key": 'dpiixeb8cnn34widwp7ihg5nzfb8eybw',
        "sys_code": '901',
        "Content-Type": "application/json"
    }   # QUESTA LINEA VA CAMBIATA PER MASCHERARE LE CREDENZIALI

    param = {
        "appkey": 'AAA324AF620903ED6ECCDDEA0B6BC866',
        "user_account": 'tecnico@zilioservice.com',
        "user_password": "monitorinG_eesco22",
        "lang": "_it_IT"

    }

    param = json.dumps(param)
    # headers = json.dumps(headers)

    URL = 'https://gateway.isolarcloud.eu/openapi/login'
    resp = requests.post(URL, headers=headers, data=param)
    resp = resp.json()
    token = resp["result_data"]["token"]

    return token


app = Dash(__name__)
colors = {
    'background': '#111111',
    'text': '#7FDBFF'
}
token = authenticateISC()


app.layout = html.Div(

    html.Div([

        html.H1('Cavarzan', style={'textAlign': 'center','backgroundColor': 'lightblue'}),
        # html.Div(id='live-update-text'),

        dcc.Graph(id='live-update-graph',style={'textAlign': 'center','backgroundColor': 'lightblue','height': '1000px'}, responsive=True),
        dcc.Interval(
            id='interval-component',
            interval=20*1000, # in milliseconds
            n_intervals=0,

        ),
    ]),

    style={'background-color': 'lightblue'}
)


@callback(Output('live-update-graph', 'figure'),
              Input('interval-component', 'n_intervals'))


def update_graph_live(n):

    df = readDataFTP()
    # queryData("Cavarzan", token)
    # df = aggregateData()
    Graph = createPlot(df)

    # Create the graph with subplots
    # fig = plotly.tools.make_subplots(rows=2, cols=1, vertical_spacing=0.2)

    return Graph


if __name__ == '__main__':


    app.run_server(host="192.168.10.229", port="9980")
    # app.run(debug=True)