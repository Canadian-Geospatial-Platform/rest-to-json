# Purpose:  This tool is supposed to extract features from an ESRI REST service
#           and create a feature class out of it.  Treatment after that is to
#           create a JSON representation of the polygonal coverage of the
#           service
#
# Author:      seagles
# first section:
# Name: Extracting Features from Map Services

# Author: Mike from SoCalGIS.org
# Organization: Southern California Government GIS User Group
# URL: https://socalgis.org/2015/08/11/extracting-features-from-map-services/
# URL: https://socalgis.org/2018/03/28/extracting-more-features-from-map-services/
# license: free to use
# adapted by: Sean Eagles
# date: March 23, 2021
#
# Created:     16-06-2021

#-------------------------------------------------------------------------------
import arcpy
import urllib2
import json
import sys
import os

def polygonTransform(FeatureClass):
    # set polygons which will be used to dissolve and create multipart
    # polygons in a single shapefile
    #
    dissolved = FeatureClass + "_dissolved"
    singlepart = FeatureClass + "_finished"

    # add field "merge"
    #
    arcpy.AddField_management(in_table=FeatureClass, field_name="MERGE", field_type="TEXT", field_precision="", field_scale="", field_length="5", field_alias="", field_is_nullable="NULLABLE", field_is_required="NON_REQUIRED", field_domain="")
    print "Field Added"

    # calculate the merge field to value 1, so that every polygon is
    # a value of 1
    arcpy.CalculateField_management(in_table=FeatureClass, field="MERGE", expression="1", expression_type="VB", code_block="")
    print "Field Calculated"

    # dissolve based on the value 1 in 'merge' field
    #
    arcpy.Dissolve_management(in_features=FeatureClass, out_feature_class=dissolved, dissolve_field="MERGE", statistics_fields="", multi_part="MULTI_PART", unsplit_lines="DISSOLVE_LINES")
    print "Features Dissolved"

    # similar to the explode tool, take all of the multipart polygons
    # and create single part polygons that are separate when not
    # attached to another polygon
    #
    arcpy.MultipartToSinglepart_management(in_features=dissolved, out_feature_class=singlepart)
    print "Multi part to single part explosion"

    # Append the result into the shapefile that has all appended
    # polygons
    #
    arcpy.Append_management(inputs=singlepart, target=ShapefileAll, schema_type="NO_TEST", field_mapping="", subtype="")

def pointTransform(FeatureClass):
    # name buffer and singlepart polygons to be created
    #
    buffer = FeatureClass + "_buffer"
    singlepart = FeatureClass + "_finished"

    # perform a buffer in the existing points which is one multipart
    # feature
    #
    arcpy.Buffer_analysis(in_features=FeatureClass, out_feature_class=buffer, buffer_distance_or_field="5 Kilometers", line_side="FULL", line_end_type="ROUND", dissolve_option="ALL", dissolve_field="", method="PLANAR")
    print "Buffer created for points - " + buffer

    # take the multipart polygon created by the dissolve and explode
    # all of the polygons into singlepart features
    #
    arcpy.MultipartToSinglepart_management(in_features=buffer, out_feature_class=singlepart)
    print "Multi part to single part explosion"

    # append the finalized polygons into one master shapefile
    #
    arcpy.Append_management(inputs=singlepart, target=ShapefileAll, schema_type="NO_TEST", field_mapping="", subtype="")

def lineTransform(FeatureClass):
    # create a name for the buffer and singlepart polygons to be created
    #
    buffer = FeatureClass + "_buffer"
    dissolved = FeatureClass + "_dissolved"
    singlepart = FeatureClass + "_finished"

    # run buffer on the feature class to create a polygon feature class
    #
    arcpy.Buffer_analysis(in_features=Shapefile, out_feature_class=buffer, buffer_distance_or_field="5000 Meters", line_side="FULL", line_end_type="ROUND", dissolve_option="NONE", dissolve_field="", method="PLANAR")
    print "Buffer created for points - " + buffer

    # add a field called "merge"
    #
    arcpy.AddField_management(in_table=buffer, field_name="MERGE", field_type="TEXT", field_precision="", field_scale="", field_length="5", field_alias="", field_is_nullable="NULLABLE", field_is_required="NON_REQUIRED", field_domain="")

    # calculate the merge field to value 1
    #
    arcpy.CalculateField_management(in_table=buffer, field="MERGE", expression="1", expression_type="VB", code_block="")
    print "Field Calculated"

    # dissolve the polygons based on the merge value of 1 creating one multipart
    # polygon
    #
    arcpy.Dissolve_management(in_features=buffer, out_feature_class=dissolved, dissolve_field="MERGE", statistics_fields="", multi_part="MULTI_PART", unsplit_lines="DISSOLVE_LINES")
    print "Features Dissolved"

    # similar to the explode tool, take the multipart polygon that was
    # created and make it into singlepart seperate polygons
    #
    arcpy.MultipartToSinglepart_management(in_features=dissolved, out_feature_class=singlepart)
    print "Multi part to single part explosion"

    # append the new polyons into the shapefile which contains all
    # polygons
    #
    arcpy.Append_management(inputs=singlepart, target=ShapefileAll, schema_type="NO_TEST", field_mapping="", subtype="")

if __name__ == '__main__':
# Setup
arcpy.env.overwriteOutput = True
baseURL = "https://gisp.dfo-mpo.gc.ca/arcgis/rest/services/FGP/Herring_Sections_Shapefile/MapServer/0"
#baseURL = "https://webservices.maps.canada.ca/arcgis/rest/services/StatCan/census_division_2016_en/MapServer/0"
fields = "*"
outdata = "C:/TEMP/data.gdb/testdata10"
gdb = "C:/TEMP/data.gdb"
gdbName = "data"
folder = "C:/TEMP"
ShapefileName = "testdata10.shp"
ShapefileAll = folder + "\\" + ShapefileName

arcpy.CreateFileGDB_management(out_folder_path=folder, out_name=gdbName, out_version="CURRENT")

try:
    # Get record extract limit
    urlstring = baseURL + "?f=json"
    j = urllib2.urlopen(urlstring)
    js = json.load(j)
    maxrc = int(js["maxRecordCount"])
    print "Record extract limit: %s" % maxrc

    # Get object ids of features
    where = "1=1"
    urlstring = baseURL + "/query?where={}&returnIdsOnly=true&f=json".format(where)
    j = urllib2.urlopen(urlstring)
    js = json.load(j)
    idfield = js["objectIdFieldName"]
    idlist = js["objectIds"]
    idlist.sort()
    numrec = len(idlist)
    print "Number of target records: %s" % numrec

    # Gather features
    print "Gathering records..."
    fs = dict()
    for i in range(0, numrec, maxrc):
        torec = i + (maxrc - 1)
        if torec > numrec:
            torec = numrec - 1
        fromid = idlist[i]
        toid = idlist[torec]
        where = "{} >= {} and {} <= {}".format(idfield, fromid, idfield, toid)
        print "  {}".format(where)
        urlstring = baseURL + "/query?where={}&returnGeometry=true&outFields={}&f=json".format(where,fields)
        fs[i] = arcpy.FeatureSet()
        fs[i].load(urlstring)

    # Save features
    print "Saving features..."
    fslist = []
    for key,value in fs.items():
        fslist.append(value)
    arcpy.Merge_management(fslist, outdata)
    print "Done!"

except:
    print "Failed"
    sys.exit()

arcpy.CreateFeatureclass_management(out_path=folder, out_name=ShapefileName, geometry_type="POLYGON", template="", has_m="DISABLED", has_z="DISABLED", spatial_reference="GEOGCS['GCS_WGS_1984',DATUM['D_WGS_1984',SPHEROID['WGS_1984',6378137.0,298.257223563]],PRIMEM['Greenwich',0.0],UNIT['Degree',0.0174532925199433]];-400 -400 1000000000;-100000 10000;-100000 10000;8.98315284119522E-09;0.001;0.001;IsHighPrecision", config_keyword="", spatial_grid_1="0", spatial_grid_2="0", spatial_grid_3="0")

arcpy.env.workspace = gdb
fcs = arcpy.ListFeatureClasses()
for fc in fcs:
    # set feature class location and name
    #
    FeatureClass = gdb + "\\" + fc
    print "Feature class: " + FeatureClass

    # Describe a feature class
    #
    desc = arcpy.Describe(FeatureClass)

    # Get the shape type (Polygon, Polyline) of the feature class
    #
    type = desc.shapeType

    print str(type)
    # If the type is polygon run through these instructions
    #
    if type == "Polygon":
        polygonTransform(FeatureClass)


    # run these instructions if type is point
    #
    elif type == "Point":
        pointTransform(FeatureClass)

    # run these instructions if type is polyline
    #
    elif type == "Polyline":
        lineTransform(FeatureClass)

#Extract shapefile names to create paths and new shapefiles from them.
#
ShapefileAllName = os.path.basename(ShapefileAll)
BaseShapefileAllName = os.path.splitext(ShapefileAllName)[0]

dissolve = folder + "\\" + BaseShapefileAllName + "_dissolve.shp"
singlepart = folder + "\\" + BaseShapefileAllName + "_singlepart.shp"
# now work on the master shapefile
# add a field called "merge"
#
arcpy.AddField_management(in_table=ShapefileAll, field_name="MERGE", field_type="TEXT", field_precision="", field_scale="", field_length="5", field_alias="", field_is_nullable="NULLABLE", field_is_required="NON_REQUIRED", field_domain="")
print "Field Added"

# calculate the merge field to value 1
#
arcpy.CalculateField_management(in_table=ShapefileAll, field="MERGE", expression="1", expression_type="VB", code_block="")
print "Field Calculated"

# dissolve the polygons based on the merge value of 1 creating one multipart
# polygon
#
arcpy.Dissolve_management(in_features=ShapefileAll, out_feature_class=dissolve, dissolve_field="MERGE", statistics_fields="", multi_part="MULTI_PART", unsplit_lines="DISSOLVE_LINES")
print "Features Dissolved"

# take the dissolved polygon and explode the single polygon into singlepart
# polygons
#
arcpy.MultipartToSinglepart_management(in_features=ShapefileAll, out_feature_class=singlepart)
print "Multi part to single part explosion"

# Add a field to count vertices "vertices"
#
arcpy.AddField_management(in_table=singlepart, field_name="VERTICES", field_type="FLOAT", field_precision="255", field_scale="0", field_length="", field_alias="", field_is_nullable="NULLABLE", field_is_required="NON_REQUIRED", field_domain="")
print "Added field VERTICES"

# Calculate the vertices field with a count of vertices in that polygon
#
arcpy.CalculateField_management(singlepart, "VERTICES", "!Shape!.pointCount-!Shape!.partCount", "PYTHON")
print "Calculate the amount of vertices in VERTICES field"

# print the count of all polygons found within the master shapefile
#
PolygonCounter = 0
with arcpy.da.SearchCursor(singlepart,"MERGE") as cursor:
    for row in cursor:
        PolygonCounter = PolygonCounter + 1
print "There are " + str(PolygonCounter) + " polygons"
del row, cursor, PolygonCounter

# create an ESRI GeoJSON for the master shapefile to be used to load into
# GeoCore
#
arcpy.FeaturesToJSON_conversion(in_features=singlepart, out_json_file="C:/TEMP/TestData_FeaturesToJSON.json", format_json="FORMATTED", include_z_values="NO_Z_VALUES", include_m_values="NO_M_VALUES", geoJSON="GEOJSON")
print "ESRI JSON created"

arcpy.Delete_management(gdb)
arcpy.Delete_management(ShapefileAll)
arcpy.Delete_management(dissolve)
arcpy.Delete_management(singlepart)