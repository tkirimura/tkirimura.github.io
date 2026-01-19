# -*- coding: utf-8 -*-

import arcpy
import json
import requests
import time
import glob
import math
import os

class Toolbox:
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "地理院ベクトルタイルデータの取得"
        self.alias = "GSIVectorTiles"
        self.description = "地理院ベクトルタイルデータの取得\n" \
                           + "国土地理院がベクトルタイル提供実験で提供しているデータを取得するツール\n" \
                           + "- 道路中心線データの取得\n" \
                           + "- 鉄道中心線データの取得\n" \
                           + "- 河川中心線データの取得\n" \
                           + "- 地形分類（自然地形）データの取得\n" \
                           + "- 地形分類（人工地形）データの取得\n" \
                           + "(c) Takashi Kirimura \n"

        # List of tool classes associated with this toolbox
        self.tools = [GSIVectorTilesRdCL, GSIVectorTilesRailCL, GSIVectorTilesRvrCL, GSIVectorTilesLFC1, GSIVectorTilesLFC2]


class GSIVectorTilesRdCL:
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "道路中心線データの取得"
        self.description = "地理院ベクトルタイル道路中心線データの取得\n" \
                           + "GSIVectorTilesRdCL\n" \
                           + "国土地理院がベクトルタイル提供実験で提供している道路中心線データ（ズームレベル16）を取得するツール\n" \
                           + "使用上の注意点\n" \
                           + "- エラーが発生して処理が終わってしまうことがあります。大規模に取得する場合はいくつかの地域で試してから実行するか、小分けにしてください。\n" \
                           + "- GeoJSONをダウンロードして処理しますが、ダウンロードしたファイルは最後に削除されます（最後のフィーチャクラスへの変換時に、プロジェクトのフォルダ内に一時的にファイルとして保存されます）。\n" \
                           + "- 国土地理院のサーバー側の状態やネットワークの状態によって、データが取得できないことがあります。\n" \
                           + "(c) Takashi Kirimura"

    def getParameterInfo(self):
        """Define the tool parameters."""
        param0 = arcpy.Parameter(
            displayName = "取得範囲",
            name="dataExtent",
            datatype="GPExtent",
            parameterType="Required",
            direction="Input")
        param1 = arcpy.Parameter(
            displayName = "出力フィーチャクラス名",
            name="outputFc",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Output")
        params = [param0, param1]
        return params

    def isLicensed(self):
        """Set whether the tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter. This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        def deg2num(lat_deg, lon_deg, zoom):
            lat_rad = math.radians(lat_deg)
            n = 1 << zoom
            xtile = int(n * ((lon_deg + 180) / 360))
            ytile = int(n * (1 - (math.log(math.tan(lat_rad) + (1 / math.cos(lat_rad))) / math.pi)) / 2)
            return xtile, ytile

        paramExtent = parameters[0].value
        ext = arcpy.Extent(parameters[0].value.XMin, parameters[0].value.YMin, \
                           parameters[0].value.XMax, parameters[0].value.YMax, \
                           None, None, None, None, parameters[0].value.spatialReference)
        srsll = arcpy.SpatialReference(6668)
        extent = ext.projectAs(srsll)
        outfc = parameters[1].value

        # URL
        ## 道路中心線
        urlBase =  "https://cyberjapandata.gsi.go.jp/xyz/experimental_rdcl/16/"
        zoom = 16

        ## ダウンロードされるファイルの名称（テンポラリ）
        areaName = "gsi16rdcl_json_temp"

        tempFol = arcpy.env.scratchFolder
        tempGdb = arcpy.env.scratchGDB
        
        min_tileX, max_tileY = deg2num(extent.YMin, extent.XMin, zoom)
        max_tileX, min_tileY = deg2num(extent.YMax, extent.XMax, zoom)
        
        tileTotal = (max_tileX - min_tileX + 1) * (max_tileY - min_tileY + 1)
        tileCount = 0
        
        arcpy.SetProgressor("step", "タイルをダウンロードしています...", 0, tileTotal + 1, 1)
        
        collection = []
        featureCollection = { "type": "FeatureCollection","features": [] }
        for x in range(min_tileX, max_tileX + 1):
            for y in range(min_tileY, max_tileY + 1):
                tileCount += 1
                arcpy.AddMessage("Tile X: " + str(x) + " Y: " + str(y) + " " + str(tileCount) + "/" + str(tileTotal))
                arcpy.SetProgressorLabel("Tile X: " + str(x) + " Y: " + str(y) + " " + str(tileCount) + "/" + str(tileTotal))
                arcpy.SetProgressorPosition()
                url = urlBase + str(x) + "/" + str(y) + ".geojson"
                response = requests.get(url)

                jsonFileName = tempFol + "/" + areaName + "_16_" + str(x) + "_" + str(y) + ".geojson"
                if response.status_code == 200:
                    jsonData = json.loads(response.content)
                    for jsonFeat in jsonData['features']:
                        if jsonFeat['properties']['Width'] == "":
                            jsonFeat['properties']['Width'] = 0
                        featureCollection['features'].append(jsonFeat)
                        
                time.sleep(0.5)

        jsonData2 = json.dumps(featureCollection, ensure_ascii=False)
        jsonFileName = tempFol + "/" + areaName + ".geojson"
        with open(jsonFileName, mode='w', encoding='UTF-8') as outf:
            outf.write(jsonData2)
        
        if len(featureCollection['features']) > 0:
            arcpy.SetProgressorLabel("フィーチャクラスに変換しています...")
            arcpy.conversion.JSONToFeatures(jsonFileName, os.path.join(tempGdb, areaName), "POLYLINE")
            arcpy.management.CopyFeatures(os.path.join(tempGdb, areaName), outfc)
        else: 
            arcpy.AddMessage("指定された範囲にデータがないか、ダウンロードできませんでした.")

        arcpy.ResetProgressor()
        arcpy.Delete_management(tempGdb)
        arcpy.Delete_management(tempFol)
        return

    def postExecute(self, parameters):
        """This method takes place after outputs are processed and
        added to the display."""
        return



class GSIVectorTilesRailCL:
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "鉄道中心線データの取得"
        self.description = "地理院ベクトルタイル道路中心線データの取得\n" \
                           + "GSIVectorTilesRailCL\n" \
                           + "国土地理院がベクトルタイル提供実験で提供している鉄道中心線データ（ズームレベル16）を取得するツール\n" \
                           + "使用上の注意点\n" \
                           + "- エラーが発生して処理が終わってしまうことがあります。大規模に取得する場合はいくつかの地域で試してから実行するか、小分けにしてください。\n" \
                           + "- GeoJSONをダウンロードして処理しますが、ダウンロードしたファイルは最後に削除されます（最後のフィーチャクラスへの変換時に、プロジェクトのフォルダ内に一時的にファイルとして保存されます）。\n" \
                           + "- 国土地理院のサーバー側の状態やネットワークの状態によって、データが取得できないことがあります。\n" \
                           + "(c) Takashi Kirimura"

    def getParameterInfo(self):
        """Define the tool parameters."""
        param0 = arcpy.Parameter(
            displayName = "取得範囲",
            name="dataExtent",
            datatype="GPExtent",
            parameterType="Required",
            direction="Input")
        param1 = arcpy.Parameter(
            displayName = "出力フィーチャクラス名",
            name="outputFc",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Output")
        params = [param0, param1]
        return params

    def isLicensed(self):
        """Set whether the tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter. This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        def deg2num(lat_deg, lon_deg, zoom):
            lat_rad = math.radians(lat_deg)
            n = 1 << zoom
            xtile = int(n * ((lon_deg + 180) / 360))
            ytile = int(n * (1 - (math.log(math.tan(lat_rad) + (1 / math.cos(lat_rad))) / math.pi)) / 2)
            return xtile, ytile

        paramExtent = parameters[0].value
        ext = arcpy.Extent(parameters[0].value.XMin, parameters[0].value.YMin, \
                           parameters[0].value.XMax, parameters[0].value.YMax, \
                           None, None, None, None, parameters[0].value.spatialReference)
        srsll = arcpy.SpatialReference(6668)
        extent = ext.projectAs(srsll)
        outfc = parameters[1].value

        # URL
        ## 鉄道中心線
        urlBase =  "https://cyberjapandata.gsi.go.jp/xyz/experimental_railcl/16/"
        zoom = 16

        ## ダウンロードされるファイルの名称（テンポラリ）
        areaName = "gsi16railcl_json_temp"

        tempFol = arcpy.env.scratchFolder
        tempGdb = arcpy.env.scratchGDB
        
        min_tileX, max_tileY = deg2num(extent.YMin, extent.XMin, zoom)
        max_tileX, min_tileY = deg2num(extent.YMax, extent.XMax, zoom)
        
        tileTotal = (max_tileX - min_tileX + 1) * (max_tileY - min_tileY + 1)
        tileCount = 0
        
        arcpy.SetProgressor("step", "タイルをダウンロードしています...", 0, tileTotal + 1, 1)
        
        collection = []
        featureCollection = { "type": "FeatureCollection","features": [] }
        for x in range(min_tileX, max_tileX + 1):
            for y in range(min_tileY, max_tileY + 1):
                tileCount += 1
                arcpy.AddMessage("Tile X: " + str(x) + " Y: " + str(y) + " " + str(tileCount) + "/" + str(tileTotal))
                arcpy.SetProgressorLabel("Tile X: " + str(x) + " Y: " + str(y) + " " + str(tileCount) + "/" + str(tileTotal))
                arcpy.SetProgressorPosition()
                url = urlBase + str(x) + "/" + str(y) + ".geojson"
                response = requests.get(url)

                jsonFileName = tempFol + "/" + areaName + "_16_" + str(x) + "_" + str(y) + ".geojson"
                if response.status_code == 200:
                    jsonData = json.loads(response.content)
                    for jsonFeat in jsonData['features']:
                        featureCollection['features'].append(jsonFeat)
                        
                time.sleep(0.5)

        jsonData2 = json.dumps(featureCollection, ensure_ascii=False)
        jsonFileName = tempFol + "/" + areaName + ".geojson"
        with open(jsonFileName, mode='w', encoding='UTF-8') as outf:
            outf.write(jsonData2)
        
        if len(featureCollection['features']) > 0:
            arcpy.SetProgressorLabel("フィーチャクラスに変換しています...")
            arcpy.conversion.JSONToFeatures(jsonFileName, os.path.join(tempGdb, areaName), "POLYLINE")
            arcpy.management.CopyFeatures(os.path.join(tempGdb, areaName), outfc)
        else: 
            arcpy.AddMessage("指定された範囲にデータがないか、ダウンロードできませんでした.")

        arcpy.ResetProgressor()
        arcpy.Delete_management(tempGdb)
        arcpy.Delete_management(tempFol)
        return

    def postExecute(self, parameters):
        """This method takes place after outputs are processed and
        added to the display."""
        return



class GSIVectorTilesRvrCL:
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "河川中心線データの取得"
        self.description = "地理院ベクトルタイル河川中心線データの取得\n" \
                           + "GSIVectorTilesRvrCL\n" \
                           + "国土地理院がベクトルタイル提供実験で提供している河川中心線データ（ズームレベル16）を取得するツール\n" \
                           + "使用上の注意点\n" \
                           + "- エラーが発生して処理が終わってしまうことがあります。大規模に取得する場合はいくつかの地域で試してから実行するか、小分けにしてください。\n" \
                           + "- GeoJSONをダウンロードして処理しますが、ダウンロードしたファイルは最後に削除されます（最後のフィーチャクラスへの変換時に、プロジェクトのフォルダ内に一時的にファイルとして保存されます）。\n" \
                           + "- 国土地理院のサーバー側の状態やネットワークの状態によって、データが取得できないことがあります。\n" \
                           + "(c) Takashi Kirimura"

    def getParameterInfo(self):
        """Define the tool parameters."""
        param0 = arcpy.Parameter(
            displayName = "取得範囲",
            name="dataExtent",
            datatype="GPExtent",
            parameterType="Required",
            direction="Input")
        param1 = arcpy.Parameter(
            displayName = "出力フィーチャクラス名",
            name="outputFc",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Output")
        params = [param0, param1]
        return params

    def isLicensed(self):
        """Set whether the tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter. This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        def deg2num(lat_deg, lon_deg, zoom):
            lat_rad = math.radians(lat_deg)
            n = 1 << zoom
            xtile = int(n * ((lon_deg + 180) / 360))
            ytile = int(n * (1 - (math.log(math.tan(lat_rad) + (1 / math.cos(lat_rad))) / math.pi)) / 2)
            return xtile, ytile

        paramExtent = parameters[0].value
        ext = arcpy.Extent(parameters[0].value.XMin, parameters[0].value.YMin, \
                           parameters[0].value.XMax, parameters[0].value.YMax, \
                           None, None, None, None, parameters[0].value.spatialReference)
        srsll = arcpy.SpatialReference(6668)
        extent = ext.projectAs(srsll)
        outfc = parameters[1].value

        # URL
        ## 河川中心線
        urlBase =  "https://cyberjapandata.gsi.go.jp/xyz/experimental_rvrcl/16/"
        zoom = 16

        ## ダウンロードされるファイルの名称（テンポラリ）
        areaName = "gsi16rvrcl_json_temp"

        tempFol = arcpy.env.scratchFolder
        tempGdb = arcpy.env.scratchGDB
        
        min_tileX, max_tileY = deg2num(extent.YMin, extent.XMin, zoom)
        max_tileX, min_tileY = deg2num(extent.YMax, extent.XMax, zoom)
        
        tileTotal = (max_tileX - min_tileX + 1) * (max_tileY - min_tileY + 1)
        tileCount = 0
        
        arcpy.SetProgressor("step", "タイルをダウンロードしています...", 0, tileTotal + 1, 1)
        
        collection = []
        featureCollection = { "type": "FeatureCollection","features": [] }
        for x in range(min_tileX, max_tileX + 1):
            for y in range(min_tileY, max_tileY + 1):
                tileCount += 1
                arcpy.AddMessage("Tile X: " + str(x) + " Y: " + str(y) + " " + str(tileCount) + "/" + str(tileTotal))
                arcpy.SetProgressorLabel("Tile X: " + str(x) + " Y: " + str(y) + " " + str(tileCount) + "/" + str(tileTotal))
                arcpy.SetProgressorPosition()
                url = urlBase + str(x) + "/" + str(y) + ".geojson"
                response = requests.get(url)

                jsonFileName = tempFol + "/" + areaName + "_16_" + str(x) + "_" + str(y) + ".geojson"
                if response.status_code == 200:
                    jsonData = json.loads(response.content)
                    for jsonFeat in jsonData['features']:
                        featureCollection['features'].append(jsonFeat)
                        
                time.sleep(0.5)

        jsonData2 = json.dumps(featureCollection, ensure_ascii=False)
        jsonFileName = tempFol + "/" + areaName + ".geojson"
        with open(jsonFileName, mode='w', encoding='UTF-8') as outf:
            outf.write(jsonData2)
        
        if len(featureCollection['features']) > 0:
            arcpy.SetProgressorLabel("フィーチャクラスに変換しています...")
            arcpy.conversion.JSONToFeatures(jsonFileName, os.path.join(tempGdb, areaName), "POLYLINE")
            arcpy.management.CopyFeatures(os.path.join(tempGdb, areaName), outfc)
        else: 
            arcpy.AddMessage("指定された範囲にデータがないか、ダウンロードできませんでした.")

        arcpy.ResetProgressor()
        arcpy.Delete_management(tempGdb)
        arcpy.Delete_management(tempFol)
        return

    def postExecute(self, parameters):
        """This method takes place after outputs are processed and
        added to the display."""
        return


class GSIVectorTilesLFC1:
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "地形分類（自然地形）データの取得"
        self.description = "地理院ベクトルタイル地形分類（自然地形）データの取得\n" \
                           + "GSIVectorTilesLFC1\n" \
                           + "国土地理院がベクトルタイル提供実験で提供している地形分類（自然地形）データ（ズームレベル14）を取得するツール\n" \
                           + "使用上の注意点\n" \
                           + "- エラーが発生して処理が終わってしまうことがあります。大規模に取得する場合はいくつかの地域で試してから実行するか、小分けにしてください。\n" \
                           + "- GeoJSONをダウンロードして処理しますが、ダウンロードしたファイルは最後に削除されます（最後のフィーチャクラスへの変換時に、プロジェクトのフォルダ内に一時的にファイルとして保存されます）。\n" \
                           + "- 国土地理院のサーバー側の状態やネットワークの状態によって、データが取得できないことがあります。\n" \
                           + "(c) Takashi Kirimura"

    def getParameterInfo(self):
        """Define the tool parameters."""
        param0 = arcpy.Parameter(
            displayName = "取得範囲",
            name="dataExtent",
            datatype="GPExtent",
            parameterType="Required",
            direction="Input")
        param1 = arcpy.Parameter(
            displayName = "出力フィーチャクラス名",
            name="outputFc",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Output")
        params = [param0, param1]
        return params

    def isLicensed(self):
        """Set whether the tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter. This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        def deg2num(lat_deg, lon_deg, zoom):
            lat_rad = math.radians(lat_deg)
            n = 1 << zoom
            xtile = int(n * ((lon_deg + 180) / 360))
            ytile = int(n * (1 - (math.log(math.tan(lat_rad) + (1 / math.cos(lat_rad))) / math.pi)) / 2)
            return xtile, ytile

        paramExtent = parameters[0].value
        ext = arcpy.Extent(parameters[0].value.XMin, parameters[0].value.YMin, \
                           parameters[0].value.XMax, parameters[0].value.YMax, \
                           None, None, None, None, parameters[0].value.spatialReference)
        srsll = arcpy.SpatialReference(6668)
        extent = ext.projectAs(srsll)
        outfc = parameters[1].value

        # URL
        ## 地形分類（自然地形）
        urlBase =  "https://cyberjapandata.gsi.go.jp/xyz/experimental_landformclassification1/14/"
        zoom = 14

        ## ダウンロードされるファイルの名称（テンポラリ）
        areaName = "gsi14lfc1_json_temp"

        tempFol = arcpy.env.scratchFolder
        tempGdb = arcpy.env.scratchGDB
        
        min_tileX, max_tileY = deg2num(extent.YMin, extent.XMin, zoom)
        max_tileX, min_tileY = deg2num(extent.YMax, extent.XMax, zoom)
        
        tileTotal = (max_tileX - min_tileX + 1) * (max_tileY - min_tileY + 1)
        tileCount = 0
        
        arcpy.SetProgressor("step", "タイルをダウンロードしています...", 0, tileTotal + 1, 1)
        
        collection = []
        featureCollection = { "type": "FeatureCollection","features": [] }
        for x in range(min_tileX, max_tileX + 1):
            for y in range(min_tileY, max_tileY + 1):
                tileCount += 1
                arcpy.AddMessage("Tile X: " + str(x) + " Y: " + str(y) + " " + str(tileCount) + "/" + str(tileTotal))
                arcpy.SetProgressorLabel("Tile X: " + str(x) + " Y: " + str(y) + " " + str(tileCount) + "/" + str(tileTotal))
                arcpy.SetProgressorPosition()
                url = urlBase + str(x) + "/" + str(y) + ".geojson"
                response = requests.get(url)

                jsonFileName = tempFol + "/" + areaName + "_14_" + str(x) + "_" + str(y) + ".geojson"
                if response.status_code == 200:
                    jsonData = json.loads(response.content)
                    for jsonFeat in jsonData['features']:
                        featureCollection['features'].append(jsonFeat)
                        
                time.sleep(0.5)

        jsonData2 = json.dumps(featureCollection, ensure_ascii=False)
        jsonFileName = tempFol + "/" + areaName + ".geojson"
        with open(jsonFileName, mode='w', encoding='UTF-8') as outf:
            outf.write(jsonData2)
        
        if len(featureCollection['features']) > 0:
            arcpy.SetProgressorLabel("フィーチャクラスに変換しています...")
            arcpy.conversion.JSONToFeatures(jsonFileName, os.path.join(tempGdb, areaName), "POLYGON")
            arcpy.management.CopyFeatures(os.path.join(tempGdb, areaName), outfc)
        else: 
            arcpy.AddMessage("指定された範囲にデータがないか、ダウンロードできませんでした.")

        arcpy.ResetProgressor()
        arcpy.Delete_management(tempGdb)
        arcpy.Delete_management(tempFol)
        return

    def postExecute(self, parameters):
        """This method takes place after outputs are processed and
        added to the display."""
        return


class GSIVectorTilesLFC2:
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "地形分類（人工地形）データの取得"
        self.description = "地理院ベクトルタイル地形分類（人工地形）データの取得\n" \
                           + "GSIVectorTilesLFC2\n" \
                           + "国土地理院がベクトルタイル提供実験で提供している地形分類（人工地形）データ（ズームレベル14）を取得するツール\n" \
                           + "使用上の注意点\n" \
                           + "- エラーが発生して処理が終わってしまうことがあります。大規模に取得する場合はいくつかの地域で試してから実行するか、小分けにしてください。\n" \
                           + "- GeoJSONをダウンロードして処理しますが、ダウンロードしたファイルは最後に削除されます（最後のフィーチャクラスへの変換時に、プロジェクトのフォルダ内に一時的にファイルとして保存されます）。\n" \
                           + "- 国土地理院のサーバー側の状態やネットワークの状態によって、データが取得できないことがあります。\n" \
                           + "(c) Takashi Kirimura"

    def getParameterInfo(self):
        """Define the tool parameters."""
        param0 = arcpy.Parameter(
            displayName = "取得範囲",
            name="dataExtent",
            datatype="GPExtent",
            parameterType="Required",
            direction="Input")
        param1 = arcpy.Parameter(
            displayName = "出力フィーチャクラス名",
            name="outputFc",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Output")
        params = [param0, param1]
        return params

    def isLicensed(self):
        """Set whether the tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter. This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        def deg2num(lat_deg, lon_deg, zoom):
            lat_rad = math.radians(lat_deg)
            n = 1 << zoom
            xtile = int(n * ((lon_deg + 180) / 360))
            ytile = int(n * (1 - (math.log(math.tan(lat_rad) + (1 / math.cos(lat_rad))) / math.pi)) / 2)
            return xtile, ytile

        paramExtent = parameters[0].value
        ext = arcpy.Extent(parameters[0].value.XMin, parameters[0].value.YMin, \
                           parameters[0].value.XMax, parameters[0].value.YMax, \
                           None, None, None, None, parameters[0].value.spatialReference)
        srsll = arcpy.SpatialReference(6668)
        extent = ext.projectAs(srsll)
        outfc = parameters[1].value

        # URL
        ## 地形分類（人工地形）
        urlBase =  "https://cyberjapandata.gsi.go.jp/xyz/experimental_landformclassification2/14/"
        zoom = 14

        ## ダウンロードされるファイルの名称（テンポラリ）
        areaName = "gsi14lfc2_json_temp"

        tempFol = arcpy.env.scratchFolder
        tempGdb = arcpy.env.scratchGDB
        
        min_tileX, max_tileY = deg2num(extent.YMin, extent.XMin, zoom)
        max_tileX, min_tileY = deg2num(extent.YMax, extent.XMax, zoom)
        
        tileTotal = (max_tileX - min_tileX + 1) * (max_tileY - min_tileY + 1)
        tileCount = 0
        
        arcpy.SetProgressor("step", "タイルをダウンロードしています...", 0, tileTotal + 1, 1)
        
        collection = []
        featureCollection = { "type": "FeatureCollection","features": [] }
        for x in range(min_tileX, max_tileX + 1):
            for y in range(min_tileY, max_tileY + 1):
                tileCount += 1
                arcpy.AddMessage("Tile X: " + str(x) + " Y: " + str(y) + " " + str(tileCount) + "/" + str(tileTotal))
                arcpy.SetProgressorLabel("Tile X: " + str(x) + " Y: " + str(y) + " " + str(tileCount) + "/" + str(tileTotal))
                arcpy.SetProgressorPosition()
                url = urlBase + str(x) + "/" + str(y) + ".geojson"
                response = requests.get(url)

                jsonFileName = tempFol + "/" + areaName + "_14_" + str(x) + "_" + str(y) + ".geojson"
                if response.status_code == 200:
                    jsonData = json.loads(response.content)
                    for jsonFeat in jsonData['features']:
                        featureCollection['features'].append(jsonFeat)
                        
                time.sleep(0.5)

        jsonData2 = json.dumps(featureCollection, ensure_ascii=False)
        jsonFileName = tempFol + "/" + areaName + ".geojson"
        with open(jsonFileName, mode='w', encoding='UTF-8') as outf:
            outf.write(jsonData2)
        
        if len(featureCollection['features']) > 0:
            arcpy.SetProgressorLabel("フィーチャクラスに変換しています...")
            arcpy.conversion.JSONToFeatures(jsonFileName, os.path.join(tempGdb, areaName), "POLYGON")
            arcpy.management.CopyFeatures(os.path.join(tempGdb, areaName), outfc)
        else: 
            arcpy.AddMessage("指定された範囲にデータがないか、ダウンロードできませんでした.")

        arcpy.ResetProgressor()
        arcpy.Delete_management(tempGdb)
        arcpy.Delete_management(tempFol)
        return

    def postExecute(self, parameters):
        """This method takes place after outputs are processed and
        added to the display."""
        return


