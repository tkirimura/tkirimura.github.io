
import arcpy
import zipfile
import os
import csv
import glob
import shutil

class Toolbox:
    def __init__(self):
        self.label = "e-Statデータの変換ツール"
        self.alias = "eStatTools"
        self.description = "e-Statの統計地理情報システムの境界データのフィーチャクラスへの変換ツールと統計データのテーブルへの変換ツール\n (c) Takashi Kirimura"

        # List of tool classes associated with this toolbox
        self.tools = [eStatPolygonToFeatureClass, eStatToTable]

class eStatPolygonToFeatureClass:
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "e-Stat境界データの変換"
        self.description = "e-Statの統計地理情報システムの境界データのフィーチャクラスへの変換\n" \
                           + "e-Statの統計地理情報システムで公開されている境界データをフィーチャクラスに変換するツール\n"

    def getParameterInfo(self):
        """Define the tool parameters."""
        param0 = arcpy.Parameter(
            displayName = "ダウンロードしたZIPファイル",
            name="zipData",
            datatype="DEFile",
            parameterType="Required",
            direction="Input")
        param0.filter.list = ['zip']

        param1 = arcpy.Parameter(
            displayName = "出力フィーチャクラス名",
            name="outputFC",
            datatype="DETable",
            parameterType="Required",
            direction="Output")

        param2 = arcpy.Parameter(
            displayName = "KEY_CODEなどでディゾルブする",
            name="execDissolve",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input")
        
        param3 = arcpy.Parameter(
            displayName = "水面調査区を除外する（国勢調査町丁・字等のみ有効）",
            name="exceptWaterZone",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input")

        params = [param0, param1, param2, param3]
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

        zipdata = parameters[0].valueAsText
        outputFC = parameters[1].valueAsText
        execDissolve = parameters[2].value
        exceptWaterZone = parameters[3].value
        
        arcpy.AddMessage(zipdata + "を処理します.")
        arcpy.AddMessage(outputFC + "に出力します.")
        arcpy.AddMessage("ディゾルブ: " + str(parameters[2].valueAsText))
        arcpy.AddMessage("水面調査区の除外: " + str(parameters[3].valueAsText))
        
        tempFol = arcpy.env.scratchFolder
        shutil.unpack_archive(zipdata, tempFol)
        shpName = ""
        for file in glob.glob(tempFol + "/*.shp"):
            shpName = file
            arcpy.AddMessage(shpName + "を処理します.")
            break

        dissolveFields = []
        summaryFields = []
        polygonType = ""
        desc = arcpy.Describe(shpName)
        orgFields = desc.fields

        for field in orgFields:
            if field.name == "HCODE":
                # HCODEがあれば国調町丁
                polygonType = "POP"
                dissolveFields = ["KEY_CODE", "PREF", "CITY", "S_AREA", "PREF_NAME", "CITY_NAME", "S_NAME", "HCODE"]
                summaryFields = [["AREA", "SUM"], ["JINKO", "SUM"], ["SETAI", "SUM"]]
                break
            elif field.name == "JIGYOSHO":
                # JIGYOSHOがあれば経済センサス・事業所統計
                polygonType = "ECO"
                dissolveFields = ["KEY_CODE", "PREF", "CITY", "S_AREA", "PREF_NAME", "CITY_NAME", "S_NAME"]
                summaryFields = [["AREA", "SUM"], ["JIGYOSHO", "SUM"], ["JUGYOSHA", "SUM"]]
                break
            elif field.name == "KCITY_N":
                # KCITY_NかKCITY_NAMEがあれば農林業センサス
                polygonType = "AG1"
                dissolveFields = ["KEY_CODE", "PREF", "CITY", "S_AREA", "PREF_NAME", "CITY_NAME", "S_NAME", "KCITY", "KCITY_N"]
                summaryFields = []
                break
            elif field.name == "KCITY_NAME":
                polygonType = "AG2"
                dissolveFields = ["KEY_CODE", "PREF", "CITY", "S_AREA", "PREF_NAME", "CITY_NAME", "S_NAME", "KCITY", "KCITY_NAME"]
                summaryFields = []
                break
        arcpy.AddMessage("POLYGONTYPE: " + polygonType)
        
        if polygonType == "POP" and exceptWaterZone == True:
            inputFeatureLayer = arcpy.management.MakeFeatureLayer(shpName, "inputFeatureLayer", "HCODE = 8101")
        else:
            inputFeatureLayer = arcpy.management.MakeFeatureLayer(shpName, "inputFeatureLayer")

        if execDissolve == True:
            arcpy.analysis.PairwiseDissolve(inputFeatureLayer, outputFC, dissolveFields, summaryFields, "MULTI_PART")
        else:
            arcpy.management.CopyFeatures(inputFeatureLayer, outputFC)

        arcpy.AddMessage(outputFC + "を出力しました.")
        arcpy.management.Delete(tempFol)
                
    def postExecute(self, parameters):
        """This method takes place after outputs are processed and
        added to the display."""
        return


class eStatToTable:
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "e-Stat統計データの変換"
        self.description = "e-Statの統計地理情報システムの統計データのテーブルへの変換\n" \
                           + "e-Statの統計地理情報システムで公開されている統計データをテーブルに変換するツール\n"

    def getParameterInfo(self):
        """Define the tool parameters."""
        param0 = arcpy.Parameter(
            displayName = "ダウンロードしたZIPファイル",
            name="zipData",
            datatype="DEFile",
            parameterType="Required",
            direction="Input")
        param0.filter.list = ['zip']
        
        param1 = arcpy.Parameter(
            displayName = "出力テーブル名",
            name="outputTable",
            datatype="DETable",
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

        zipdata = parameters[0].valueAsText
        tableName = parameters[1].valueAsText
        arcpy.AddMessage(zipdata + "を処理します.")

        with zipfile.ZipFile(zipdata) as zfile:
            files = zfile.namelist()
            with zfile.open(files[0]) as f:
                arcpy.AddMessage(files[0] + "を変換します.")
                data = f.read().decode('cp932').splitlines()
                reader = csv.reader(data)

                row1 = next(reader)
                row2 = next(reader)

                f = 0
                numFields = []
                tblFields = []
                fieldNames = []
                for field in zip(row1, row2):
                    fInfo = arcpy.Field()
                    if field[1] == '':
                        fInfo.name = field[0]
                        fInfo.aliasName = field[0]
                        fInfo.type = "String"
                        fInfo.length = 2000
                        fInfo.editable = True
                        fInfo.required = False
                        fInfo.isNullable = True
                    else:
                        fInfo.name = field[0]
                        fInfo.aliasName = field[1].strip()
                        fInfo.type = "LONG"
                        fInfo.editable = True
                        fInfo.required = False
                        fInfo.isNullable = True
                        numFields.append(f)
                    tblFields.append(fInfo)
                    fieldNames.append(field[0])
                    f += 1

                # 数値フィールドの値判定（Double or Integer）を最初の100行で。
                arcpy.AddMessage("数値フィールドの型を判定しています.")
                checkRows = max(100, len(data) - 2)
                rowBuf = []
                i = 0
                for row in reader:
                    i += 1
                    if i < checkRows:
                        rowBuf.append(row)
                    elif i == checkRows:
                        for cRow in rowBuf:
                            for j in numFields:
                                if not tblFields[j].type == "Double":
                                    if (not cRow[j] == '*') and (not cRow[j] == 'X') and (not cRow[j] == '-') and (not cRow[j] == 'Y') and (not cRow[j] == '') and (not cRow[j] == 'x'):
                                        checkNum = float(cRow[j])
                                        if not checkNum.is_integer():
                                            tblFields[j].type = "Double"
                                            break

                        arcpy.AddMessage("テーブルを作成しています.")
                        arcpy.da.CreateTable(tableName, tblFields)
                        with arcpy.da.InsertCursor(tableName, fieldNames) as cur:
                            for cRow in rowBuf:
                                for j in numFields:
                                    if cRow[j] == '*' or cRow[j] == 'X' or cRow[j] == 'Y' or cRow[j] == '' or cRow[j] == 'x':
                                        cRow[j] = None
                                    elif cRow[j] == '-':
                                        cRow[j] = '0'
                                cur.insertRow(cRow)
                    else:
                        with arcpy.da.InsertCursor(tableName, fieldNames) as cur:
                            for j in numFields:
                                if row[j] == '*' or row[j] == 'X' or row[j] == 'Y' or row[j] == '' or row[j] == 'x':
                                    row[j] = None
                                elif row[j] == '-':
                                    row[j] = '0'
                            cur.insertRow(row)
        arcpy.AddMessage(tableName + "を出力しました.")
                
    def postExecute(self, parameters):
        """This method takes place after outputs are processed and
        added to the display."""
        return


