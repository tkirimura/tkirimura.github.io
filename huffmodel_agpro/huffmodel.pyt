# -*- coding: utf-8 -*-

import arcpy


class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Toolbox"
        self.alias = ""

        # List of tool classes associated with this toolbox
        self.tools = [HuffModelAnalysis]


class HuffModelAnalysis(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "ハフモデル分析"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""

        param0 = arcpy.Parameter(
            displayName="店舗レイヤー（ポイント）",
            name="stores_layer",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")

        param1 = arcpy.Parameter(
            displayName="魅力度フィールド",
            name="attractiveness_field",
            datatype="Field",
            parameterType="Optional",
            direction="Input")
        param1.parameterDependencies = [param0.name]

        param2 = arcpy.Parameter(
            displayName="需要レイヤー（ポイント）",
            name="demand_layer",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")

        param3 = arcpy.Parameter(
            displayName="集計フィールド",
            name="stat_fields",
            datatype="field",
            parameterType="Required",
            direction="Input",
            multiValue=True)

        param3.parameterDependencies = [param2.name]
        #param3.columns = [['Field', 'フィールド'], ['GPString', '集計方法']]
        #param3.filters[1].type = 'ValueList'
        #param3.values = [['NAME', 'SUM']]
        #param3.filters[1].list = ['SUM', 'MIN', 'MAX', 'STDEV', 'MEAN']

        param4 = arcpy.Parameter(
            displayName="距離抵抗(1.0-2.0)",
            name="distance_decay",
            datatype="GPDouble",
            parameterType="Required",
            direction="Input")

        param4.filter.type = "Range"
        param4.filter.list = [1.0, 2.0]
        param4.value = 2.0

        param5 = arcpy.Parameter(
            displayName="検索半径(単位：メートル)",
            name="search_radius",
            datatype="GPDouble",
            parameterType="Required",
            direction="Input")

        param5.filter.type = "Range"
        param5.filter.list = [0, 100000]
        param5.value = 2000

        param6 = arcpy.Parameter(
            displayName="出力テーブル",
            name="output_table",
            datatype="DETable",
            parameterType="Required",
            direction="Output")
        param6.parameterDependencies = [param0.name]
        
        params = [param0, param1, param2, param3, param4, param5, param6]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""

        # GenerateNearTable
        messages.addMessage("'近接情報テーブルの生成'を実行しています.")
        
        in_features = parameters[0].valueAsText
        near_features = parameters[2].valueAsText
        outtable = "in_memory/neartable"

        search_radius = parameters[5].valueAsText + ' Meters'
        location = 'NO_LOCATION'
        angle = 'NO_ANGLE'
        closest = 'ALL'

        arcpy.GenerateNearTable_analysis(in_features, near_features, outtable, search_radius,
                                         location, angle, closest, 0)

        # Join 
        messages.addMessage("'テーブル結合'を実行しています(1/2).")

        joined_table1 = arcpy.AddJoin_management(outtable, "IN_FID", in_features, "OBJECTID")

        messages.addMessage("'テーブル結合'を実行しています(2/2).")

        joined_table2 = arcpy.AddJoin_management(joined_table1, "NEAR_FID", near_features, "OBJECTID")
        basetable = "in_memory/base_table"
        arcpy.CopyRows_management(joined_table2, basetable)

        # Calculate Values
        messages.addMessage("吸引率を計算しています(1/2).")

        attract_expression = "(!" + in_features + "_" + parameters[1].valueAsText + "! * 10000) / pow(!neartable_NEAR_DIST!, " + parameters[4].valueAsText + ")"
        #messages.addMessage("吸引率の計算式: " + attract_expression)

        arcpy.AddField_management(basetable, "attract_param1", "DOUBLE")
        arcpy.CalculateField_management(basetable, "attract_param1", attract_expression, "PYTHON3")

        messages.addMessage("吸引率を計算しています(2/2).")
        sumtable = "in_memory/sumtable"
        arcpy.Statistics_analysis(basetable, sumtable, [["attract_param1", "SUM"]], parameters[2].valueAsText + "_OBJECTID")

        joined_table3 = arcpy.AddJoin_management(basetable, parameters[2].valueAsText + "_OBJECTID", sumtable, parameters[2].valueAsText + "_OBJECTID")
        calctable = "in_memory/calctable"
        arcpy.CopyRows_management(joined_table3, calctable)

        messages.addMessage("需要レイヤーの値を集計しています.")
        calcFields = parameters[3].valueAsText.split(";")
        calcflist = []
        for fieldName in calcFields:
            calc_expression = "(!base_table_attract_param1! / !sumtable_SUM_attract_param1!) * !base_table_" + near_features + "_" + fieldName + "!"
            arcpy.AddField_management(calctable, "calctable_" + fieldName, "DOUBLE")
            #messages.addMessage(calc_expression)
            arcpy.CalculateField_management(calctable, "calctable_" + fieldName, calc_expression, "PYTHON3")
            calcflist.append(["calctable_" + fieldName, "SUM"])

        fin_table0 = "in_memory/final_table"
        arcpy.Statistics_analysis(calctable, fin_table0, calcflist, "base_table_" + in_features + "_OBJECTID")

        arcpy.AlterField_management(fin_table0, "base_table_" + in_features + "_OBJECTID", in_features + "_OBJECTID", in_features + "_OBJECTID")
        for fieldName in calcFields:
            arcpy.AlterField_management(fin_table0, "SUM_calctable_" + fieldName, "SUM_" + fieldName, "SUM_" + fieldName)

        final_table = parameters[6].valueAsText
        messages.addMessage("出力テーブルを作成しています.")
        arcpy.CopyRows_management(fin_table0, final_table)
        return

