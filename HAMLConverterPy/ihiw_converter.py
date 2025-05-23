import argparse
from math import isnan
from math import nan
import xml.etree.ElementTree as ET #using System.Xml;
from lxml import etree
import pandas as pd
import datetime
import csv
import copy

####################
# CONVERTER CLASS
####################
''' <summary>
    /// Script was converted to Python by Teresa Tavella
    /// University of Bologna
    /// https://github.com/TessaTi/IHIW_Converter_py
    /// Script was modified to newer standards (HAML 0.4.4) by Livia Tran and William Lemieux
    /// 
    /// Determines the manufacturer of the input file.
    /// The manufacturer can be Immucor or OneLambda.
    /// Immucor provides a file delimited with ",".
    /// OneLambda provides a file delimited with ";".
    /// In order to determine the manufacturer all columns must be present.
    /// If no manufacturer can be determined the manufacturer string will be empty.
    ///<summary>
 '''


def appendFeedback(newFeedback=None, validationFeedback=None):
    if(newFeedback in validationFeedback):
        pass
    else:
        validationFeedback += (newFeedback + ';\n')
    return validationFeedback

class Converter(object):

    def __init__(self, csvFileName=None, manufacturer=None, xmlFile=None, labID=None):
        self.csvFileName = csvFileName
        self.manufacturer = manufacturer
        self.allFieldsQuoted = None
        self.xmlFile = xmlFile
        self.xmlText = None
        self.xmlData = None
        # There are localization settings in the output files.
        # Different files are delimited by commas and semicolons. Different files use . or , as a decimal.
        # This needs to be accounted for.
        self.delimiter = None
        #self.decimal = None
        self.dateFormat = '%d-%m-%Y'
        self.validationFeedback=''
        self.labID = labID

    def formatRunDate(self, RunDate=None):
        # format the date to the correct haml (ISO) style.
        # Parse the date
        try:
            dateObject = datetime.datetime.strptime(RunDate, self.dateFormat)
            formattedRunDate = dateObject.strftime("%Y-%m-%d")
            return formattedRunDate
        except Exception as e:
            print('Could not format the date properly:' + str(e))
            self.DetermineDateFormat(RunDate)
            if (self.dateFormat is not None):
                dateObject = datetime.datetime.strptime(RunDate, self.dateFormat)
                formattedRunDate = dateObject.strftime("%Y-%m-%d")
                return formattedRunDate
            else:
                print('Cannot interpret date format! ' + RunDate)
                return None

    def DetermineDateFormat(self, dateString=None):
        print('Determining Date format of this string:' + dateString)
        self.dateFormat = None
        # TODO: Is there a more flexible way to do this? This breaks regularly with new date formats.
        # TODO: Warning: It's very easy to mis-interpret days and months here.
        # TODO: We can try to parse the whole document....to find a date > 12
        potentialDateFormats=['%d-%m-%Y', '%Y-%m-%d', '%d-%b-%Y','%d/%m/%Y','%m/%d/%Y','%d.%m.%Y','%d. %m. %Y']
        for dateFormat in potentialDateFormats:
            try:
                dateObject = datetime.datetime.strptime(dateString, dateFormat)
                print('I believe that ' + dateString + ' is indeed this format:' + str(dateFormat))
                self.dateFormat=dateFormat
            except Exception as e:
                pass
                #print(dateString + ' is not this format:' + str(dateFormat))
        if(self.dateFormat is None):
            print('Failed at determining date format! ')
            raise Exception('Could not determine Date Format of this string:' + str(dateString))

    def determineFormatAndManufacturer(self):
        print('Determining File Format and Manufacturer')

        # Possible delimiters
        tryDelimiters=[',',';','\t']
        for delimiter in tryDelimiters:
            if (self.delimiter is None):

                # Pandas CSV reader likes to specify the quoting behavior. Sometimes in CSV files all the columns are quoted, sometimes they aren't.
                # Lets check both cases.
                for checkAllFieldsQuoted in [True, False]:
                    try:
                        print('Checking if this file has a (' + str(delimiter) + ') delimiter,  checkAllFieldsQuoted=' + str(checkAllFieldsQuoted))
                        pandasCsvReader = readCsvFile(csvFileName=self.csvFileName, delimiter=delimiter, allFieldsQuoted=checkAllFieldsQuoted)
                        self.determineManufacturer(pandasCsvReader=pandasCsvReader)
                        print('Manufacturer:' + str(self.manufacturer))
                        if(self.manufacturer is not None):
                            # That worked! Remember these settings
                            self.delimiter=delimiter
                            self.allFieldsQuoted=checkAllFieldsQuoted
                            break
                    except Exception as e:
                        print('Exception when reading Csv File (delimiter=' + str(delimiter) + ' allFieldsQuoted=' + str(checkAllFieldsQuoted) + '):' + str(e))

    def determineManufacturer(self, pandasCsvReader=None):
        colOneLambda = ['PatientID', 'SampleIDName', 'RunDate', 'CatalogID', 'BeadID', 'Specificity', 'RawData','NC1BeadID','PC1BeadID', 'NC2BeadID','PC2BeadID', 'Rxn']
        colImmucorOld = ['Sample ID', 'Patient ID', 'Lot ID', 'Run Date', 'Allele', 'Assignment', 'Raw Value']
        colImmucor = ['Sample ID', 'Patient Name', 'Lot ID', 'Run Date', 'Allele', 'Assignment', 'Raw Value']

        if(self.manufacturer is None):

            # Get the columns from the csvReader:
            # These replaces are to get rid of space characters.
            # The \ufeff" character seems to indicate the encoding of the file.
            # The proper solution is to switch the codec the file is decoded in, but instead I'm doing a replace, because it's easier.
            colnames = [str(c.strip('"').strip().replace(' ', '_').replace('\ufeff"','')) for c in pandasCsvReader.columns.tolist()]
            print('I found these columns (N='+ str(len(colnames)) + ') :' + str(colnames))

            # Check if there is an intersection of the sets. Overlapping is good.
            # Does this work? think this will break if there are any overlapping column names. But there arent!
            if (set(colnames) & set(colImmucor) or set(colnames) & set(colImmucorOld)):
                self.manufacturer = 'Immucor'
                print('This is an Immucor File.')
            elif (set(colnames) & set(colOneLambda)):
                self.manufacturer = 'OneLambda'
                print('This is a One Lambda File.')
            else:
                print('Cannot determine manufacturer based on those column names.')

    #########
    # Get bead value
    #########
    def GetBeadValue(self,NC2BeadID=None, BeadID=None, SampleIDName=None, SampleID=None,RawData=None):
        if BeadID == NC2BeadID and SampleIDName == SampleID:
            # Some localizations allow a comma in these as a decimal format. Just make it a period.
            BeadValue = str(RawData).replace(',','.')
        else:
            BeadValue = 0
        return BeadValue

    #########
    # Prettify xml
    ######### 
    def prettyPrintXml(self):
        # Generate xml text
        xmlText = self.xmlData.decode()
        self.xmlText = xmlText

        if(self.xmlText is not None and len(self.xmlText) > 0):
            #print('***xml Text:\n' + str(self.xmlText))
            rootElement = etree.fromstring(self.xmlText)
            prettyPrintText=etree.tostring(rootElement, pretty_print=True).decode()
            if(prettyPrintText is not None and len(prettyPrintText) > 0):
                self.xmlText = prettyPrintText

            if (self.xmlFile is not None):
                elementTree = etree.ElementTree(rootElement)
                elementTree.write(self.xmlFile, pretty_print=True, encoding='utf-8')
            else:
                print('Not writing xml text to file, because None was provided for xmlFile parameter')


    #################
    # Parse OneLambda
    #################
    def ProcessOneLambda(self, pandasCsvReader=None):
        print('OneLambda to xml...')
        validationFeedback = ''

        try:
            # Data is the root element.
            data = ET.Element("haml",xmlns='urn:HAML.Namespace', version = "0.4.4")
            # OLReader is a pandas DataFrame.
            # Each row is a namedtuple
            # The first row contains the negative control info.
            # The second row contains positive control info.
            reportingCenter = makeSubElement(data, 'reporting-center')
            reportingCenter.text = self.labID

            documentContext = makeSubElement(data, 'document-context')
            documentContext.text = 'Sample document context for working purposes'

            # State variable to iterate through. States cycle through negative_control->positive_control->bead_values
            readerState = 'negative_control'
            negativeControlRow=None
            positiveControlRow=None
            patientID='!!!'
            sampleID = '!!!'
            catalogID = ''
            interpretation = None

            #rowlength = OLReader.shape[0]
            for line, row in enumerate(pandasCsvReader.itertuples(), 1):

                #print('row:' + str(row))

                currentRowSampleIDName = str(row.SampleIDName).strip()
                currentRowPatientID = str(row.PatientID).strip()
                currentRowCatalogID = str(row.CatalogID).strip()


                # Some quick error checking..
                # In one case the user submitted data that was missing sampleIDs. This shouldn't be accepted.
                # print('delimiter =(' + self.delimiter + ')')
                # print('sampleIDName= ' + str(row.SampleIDName))
                if (currentRowSampleIDName is None or len(currentRowSampleIDName) == 0 or currentRowSampleIDName == 'nan'):
                    # row.SampleIDName='?'
                    currentRowSampleIDName = '?'
                    feedbackText = 'Empty SampleIDName found, please provide SampleIDName in every row.'
                    validationFeedback = appendFeedback(validationFeedback=validationFeedback, newFeedback=feedbackText + ' Row=' + str(row.Index))

                if (currentRowPatientID is None or len(currentRowPatientID) == 0 or currentRowPatientID == 'nan'):
                    currentRowPatientID = '?'
                    feedbackText = 'Empty PatientID found, please provide PatientID in every row.'
                    validationFeedback = appendFeedback(validationFeedback=validationFeedback, newFeedback=feedbackText + ' Row=' + str(row.Index))

                # State Machine Logic:
                # First row is negative control
                # Second row is positive control
                # Many rows of bead_values
                # Possibly circle back with another negative control.
                if(readerState=='negative_control'):
                    negativeControlRow = row
                    readerState='positive_control'
                elif(readerState=='positive_control'):
                    positiveControlRow = row
                    readerState = 'bead_values'

                    # For each new patient or sample, we need to add the patient-antibody-assessment and solid-phase-panel nodes
                    # TODO: Note to self, i removed this If statement. I need to make these nodes whenever we leave the positive control state.
                    # Probably these comments can be removed if this works.....
                    #if (currentRowSampleIDName != sampleID or currentRowPatientID != patientID):


                    # Store some data for the current patient/sample/panel
                    sampleID = currentRowSampleIDName
                    patientID = currentRowPatientID

                    try:
                        negativeControlMFI = str(int(round(float(str(negativeControlRow.RawData).replace(',', '.')))))
                        positiveControlMFI = str(int(round(float(str(positiveControlRow.RawData).replace(',', '.')))))
                    except Exception as e:
                        negativeControlMFI = '-1'
                        positiveControlMFI = '-1'
                        print('Could not identify values for negative control(' + str(negativeControlRow.RawData)
                              + ') or positive control(' + str(positiveControlRow.RawData)
                              + '). SampleID = ' + str(currentRowSampleIDName) + '. PatientID = ' + str(
                            currentRowPatientID) + '. Data was in an unexpected format.')
                        print('Exception:' + str(e))

                    patientElement = makeSubElement(data, 'patient',
                                                                 {'patient-id': patientID})

                    sampleElement = makeSubElement(patientElement, 'sample',
                                                                {'sample-id': sampleID,
                                                                 'testing-laboratory': self.labID})

                    assayElement = makeSubElement(sampleElement, 'assay',
                                                                {'assay-date': self.formatRunDate(row.RunDate),
                                                                 })

                    workingSampleElement = makeSubElement(assayElement, 'working-sample',
                                                               {'working-sample-id': str(sampleID)})

                    # For any new sampleID or patientID,  this is a new solid-phase-panel.
                    # TODO: We also need this If the catalogID has changed. If there are multiple catalogs in the input csv there should be new solid-phase panel for each.
                    #   For now it works that we're creating new patient-antibody-assessment AND a new solid-phase-panel for every change.
                    catalogID = currentRowCatalogID
                    # print('Found a new bead catalog: ' + str(catalogID))

                    solidPhasePanel = makeSubElement(workingSampleElement, 'solid-phase-panel', None)
                    kitManufacturer = makeSubElement(solidPhasePanel, 'kit-manufacturer')
                    kitManufacturer.text = self.manufacturer

                    lot = makeSubElement(solidPhasePanel, 'lot-number')
                    lot.text = catalogID

                elif(readerState=='bead_values'):
                    if row.PatientID is None:
                        # If we get here then there actually might be a problem.
                        print('Reached the end of the input csv, breaking the loop. This means there was a newline at the end of the .csv, possibly malformed data.')
                        break

                    else:
                        # TODO: Consider writing each sample to an individual HAML file. This would need to create child elements for each HAML.
                        #   We kind of want to do that with HML as well. Issue 189 on Github

                        # If the patientID, sampleID, or catalogID have changed, we need to define a new patient-antibody-assessment. This should be on a negative control row currently.
                        if (currentRowSampleIDName != sampleID or currentRowPatientID != patientID or currentRowCatalogID != catalogID):
                            #print(' I detected a new Sample or Patient or Catalog ID. This should be the negative control row:' + str(row))
                            negativeControlRow = row
                            readerState = 'positive_control'
                            interpretation = None

                        else:
                            # Parse the allele specificities, Ranking, and MFI
                            # Are Specificities ever going to be delimited by something other than commas? Is that possible?
                            Specs = row.Specificity.split(",")
                            try:
                                Raw = int(round(float(str(row.RawData).replace(',','.'))))
                                #print('Raw:' + str(Raw))
                            except Exception as e:
                                Raw = -1
                                print('Could not identify values for raw MFI(' + str(row.RawData)
                                      + ') . SampleID = ' + str(currentRowSampleIDName) + '. PatientID = ' + str(currentRowPatientID) + '. Data was in an unexpected format.')
                                print('Exception:' + str(e))
                            
                            try:
                                Norm = int(round(float(str(row.NormalValue).replace(',','.'))))
                                #print('Norm:' + str(Norm))
                            except Exception as e:
                                Norm = -1
                                print('Could not identify values for raw MFI(' + str(row.NormalValue)
                                      + ') . SampleID = ' + str(currentRowSampleIDName) + '. PatientID = ' + str(currentRowPatientID) + '. Data was in an unexpected format.')
                                print('Exception:' + str(e))
                            # TODO: We're not assigning the ranking in the best way.
                            #  A better strategy is to load all the MFIs and give them a ranking. Before writing the values. Add this logic.
                            try:
                                Ranking = str(int(row.Rxn))
                                #print('This row seems fine:'                   + '\n' + str(row))
                            except Exception as e:
                                Ranking = -1
                                print('Could not identify values for Ranking(' + str(row.Rxn)
                                      + ') . SampleID = ' + str(currentRowSampleIDName)
                                      + '. PatientID = ' + str(currentRowPatientID)
                                      + '. Data was in an unexpected format:'
                                      + '\n' + str(row))
                                print('Exception:' + str(e))

                            # What locus is this data row for?
                            locusDataRow=''
                            for currentLocus in Specs:
                                if(currentLocus != '-'):
                                    if(locusDataRow==''):
                                        # The only (or first) locus encountered.
                                        locusDataRow=currentLocus
                                    else:
                                        # The second locus encountered for the heterodimer.
                                        locusDataRow=locusDataRow+ '&' + currentLocus
                                else:
                                    pass

                            beadElement = makeSubElement(solidPhasePanel, 'bead', None)
                            beadInfo = makeSubElement(beadElement, 'bead-info',
                                                      {'bead-id': str(row.BeadID),
                                                          'HLA-target-type':str(locusDataRow)
                                            })

                            rawData = makeSubElement(beadElement, 'raw-data', {'sample-raw-MFI': str(Raw)})
                            adjustedData = makeSubElement(beadElement, 'converted-data', {'sample-adjusted-MFI': str(Norm)})
                            beadInterp = makeSubElement(adjustedData, 'bead-interpretation', 
                                                        {'classification-entity': 'One Lambda Software',
                                                        'bead-rank': str(Ranking)})

                            if (interpretation == None):
                                try:
                                    alI = str(row.Antibody_FinalAssignment_Class_I)
                                    alII = str(row.Antibody_FinalAssignment_Class_II)
                                    if (alI != "" and alI != "nan"):
                                        if (alII != "" and alII != "nan"):
                                            alstring = alI.replace(",","+") + "+" + alII.replace(",","+")
                                        else:
                                            alstring = alI.replace(",","+")
                                    else:
                                        if (alII != "" and alII != "nan"):
                                            alstring = alII.replace(",","+")
                                        else:
                                            alstring = ""
                                    interpretation = alstring
                                except Exception as e:
                                    print("Error handling " + str(row.Antibody_FinalAssignment_Class_I) + "/" + str(row.Antibody_FinalAssignment_Class_II))
                                    print('Exception:' + str(e))
                                    alstring = ""

                                InterpretationElement = ET.SubElement(assayElement, 'interpretation')
                                PosSpecElement = ET.SubElement(InterpretationElement, 'positive-specificities')
                                PosSpecElement.text = str(alstring)

                            

            # create a new XML file with the results
            self.xmlData = ET.tostring(data)
            self.prettyPrintXml()
        except Exception as e:
            validationFeedback+= 'Exception when reading file:' + str(e) + ';\n'
        return validationFeedback

    ########
    # Parse Immucor
    ########
    def ProcessImmucor(self, pandasCsvReader=None, reportingCenterID='?'):
        print('Immucor to xml...')
        validationFeedback = ''
        switcher = {'Positive':8, 'Weak':6, 'Negative':2}

        try:
            # Data is the root element.
            data = ET.Element("haml",xmlns='urn:HAML.Namespace', version = "0.4.4")
            # Each row is a namedtuple
            reportingCenter = makeSubElement(data, 'reporting-center')
            reportingCenter.text = self.labID

            documentContext = makeSubElement(data, 'document-context')
            documentContext.text = 'Sample document context for working purposes'
            
            interpretation = None
            Specs = None
            BID = None
            patientID='!!!'
            sampleID = '!!!'
            catalogID = ''

            #rowlength = OLReader.shape[0]
            for line, row in enumerate(pandasCsvReader.itertuples(), 1):

                #print('row:' + str(row))

                currentRowSampleIDName = str(row.SampleID).strip()
                currentRowPatientID = str(row.PatientName).strip()
                currentRowCatalogID = str(row.LotID).strip()


                # Some quick error checking..
                # In one case the user submitted data that was missing sampleIDs. This shouldn't be accepted.
                # print('delimiter =(' + self.delimiter + ')')
                # print('sampleIDName= ' + str(row.SampleIDName))
                if (currentRowSampleIDName is None or len(currentRowSampleIDName) == 0 or currentRowSampleIDName == 'nan'):
                    currentRowSampleIDName = '?'
                    feedbackText = 'Empty SampleIDName found, please provide SampleIDName in every row.'
                    validationFeedback = appendFeedback(validationFeedback=validationFeedback, newFeedback=feedbackText + ' Row=' + str(row.Index))

                if (currentRowPatientID is None or len(currentRowPatientID) == 0 or currentRowPatientID == 'nan'):
                    currentRowPatientID = '?'
                    feedbackText = 'Empty PatientID found, please provide PatientID in every row.'
                    validationFeedback = appendFeedback(validationFeedback=validationFeedback, newFeedback=feedbackText + ' Row=' + str(row.Index))

                # Store some data for the current patient/sample/panel
                if row.PatientName is None:
                        # If we get here then there actually might be a problem.
                        print('Reached the end of the input csv, breaking the loop. This means there was a newline at the end of the .csv, possibly malformed data.')
                        break

                if (currentRowSampleIDName != sampleID or currentRowPatientID != patientID or currentRowCatalogID != catalogID):
                    
                    interpretation = None
                    Specs = None
                    BID = None
                    sampleID = currentRowSampleIDName
                    patientID = currentRowPatientID

                    patientElement = makeSubElement(data, 'patient',
                                                                 {'patient-id': patientID})

                    sampleElement = makeSubElement(patientElement, 'sample',
                                                                {'sample-id': sampleID,
                                                                 'testing-laboratory': self.labID})

                    try:
                        runDate = row.RunDate
                        runDate = self.formatRunDate(runDate)
                        assayElement = makeSubElement(sampleElement, 'assay',
                                                                {'assay-date': self.formatRunDate(row.RunDate)})
                    except Exception as e:
                        assayElement = makeSubElement(sampleElement, 'assay')
                

                    workingSampleElement = makeSubElement(assayElement, 'working-sample',
                                                               {'working-sample-id': str(sampleID)})

                    catalogID = currentRowCatalogID

                    solidPhasePanel = makeSubElement(workingSampleElement, 'solid-phase-panel', None)
                    kitManufacturer = makeSubElement(solidPhasePanel, 'kit-manufacturer')
                    kitManufacturer.text = self.manufacturer

                    lot = makeSubElement(solidPhasePanel, 'lot-number')
                    lot.text = catalogID

                    # TODO: Consider writing each sample to an individual HAML file. This would need to create child elements for each HAML.
                    #   We kind of want to do that with HML as well. Issue 189 on Github


                # Parse the allele specificities, Ranking, and MFI
                # Are Specificities ever going to be delimited by something other than commas? Is that possible?
                Specs = row.Allele
                try:
                    Raw = int(round(float(str(row.RawValue).replace(',','.'))))
                    #print('Raw:' + str(Raw))
                except Exception as e:
                    Raw = -1
                    print('Could not identify values for raw MFI(' + str(row.RawValue)
                                + ') . SampleID = ' + str(currentRowSampleIDName) + '. PatientID = ' + str(currentRowPatientID) + '. Data was in an unexpected format.')
                    print('Exception:' + str(e))

                try:
                    assn = row.Assignment
                    rank = switcher[assn]
                except Exception as e:
                    assn = "Undetermined"
                    rank = "Undetermined" 
                    print('Could not identify assignment and rank (' + str(row.Assignment)
                                + ') . SampleID = ' + str(currentRowSampleIDName) + '. PatientID = ' + str(currentRowPatientID) + '. Data was in an unexpected format.')
                    print('Exception:' + str(e))
                            
                try:
                    Norm = int(round(float(str(row.MFI_LRA).replace(',','.'))))
                    #print('Norm:' + str(Norm))
                except Exception as e:
                    Norm = -1
                    print('Could not identify values for normalized value (' + str(row.NormalValue)
                        + ') . SampleID = ' + str(currentRowSampleIDName) + '. PatientID = ' + str(currentRowPatientID) + '. Data was in an unexpected format.')
                    print('Exception:' + str(e))
                # TODO: We're not assigning the ranking in the best way.
                #  A better strategy is to load all the MFIs and give them a ranking. Before writing the values. Add this logic.
                try:
                    currentBID = row.AntigenID
                except Exception as e:
                    currentBID = row.Bead_ID
                if (BID != currentBID):
                    # What allele is this data row for?
                    locusDataRow = Specs

                    beadElement = makeSubElement(solidPhasePanel, 'bead', None)
                    beadInfo = makeSubElement(beadElement, 'bead-info')
                    BIDElement = ET.SubElement(beadInfo, 'bead-id')
                    BIDElement.text = str(currentBID)
                    HLAElement = ET.SubElement(beadInfo, 'HLA-target-type')
                    HLAElement.text = str(locusDataRow)

                    rawData = makeSubElement(beadElement, 'raw-data', {'sample-raw-MFI': str(Raw)})
                    adjustedData = makeSubElement(beadElement, 'converted-data', {'sample-adjusted-MFI': str(Norm)})
                    beadInterp = makeSubElement(adjustedData, 'bead-interpretation', 
                                                {'classification-entity': 'Immucor Software',
                                                    'bead-classification': assn,
                                                    'bead-rank': str(rank)})
                else:
                    HLAElement.text = str(locusDataRow+"&"+Specs)
                BID = currentBID

                try:
                    if (row.IsAssigned == "YES"):
                        if (interpretation == "" or interpretation is None):
                            interpretation = row.Allele
                            InterpretationElement = ET.SubElement(assayElement, 'interpretation')
                            PosSpecElement = ET.SubElement(InterpretationElement, 'positive-specificities')
                            PosSpecElement.text = str(interpretation)
                        else:
                            interpretation = interpretation + "+" + row.Allele
                            PosSpecElement.text = str(interpretation)
                        
                except Exception as e:
                    print("Error handling " + str(row.Allele) + "/" + str(row.IsAssigned))
                    print('Exception:' + str(e))
                            

            # create a new XML file with the results
            self.xmlData = ET.tostring(data)
            self.prettyPrintXml()
        except Exception as e:
            validationFeedback+= 'Exception when reading file:' + str(e) + ';\n'
        return validationFeedback
 


    def convert(self):
        # This should be theoretically easy. But it's not really,
        # TODO: Because there are inconsistencies in the formats of the input files:
        # Things that We must detect and react to:
        # 1) Manufacturer, the Immucor and One Lambda kits use different column names in their export files.
        # 2) Delimiter. Exporters do not use a consistent delimiter, I must detect if csv are separated by comma, semicolon, tab, Other?
        # 3) Field Quoting. Sometimes the csv files use quotes around every text field, sometimes they don't. CSV readers need to know the quoting behavior.
        # 4) Decimals. Sometimes they use a "." sometimes they use ",". Different countries use different formats
        # 5) Date formats. One Lambda software at least uses the local settings for date formats. We're accepting a few formats here but we should limit it to only ISO format (YYYY-MM-DD)
        # 6) Control Bead Formats. How do the manufacturers specify what the control beads are? This varies among files from the same manufacturer, and seems to be based on user settings?
        # 7) Specificity formats. For One Lambda it seems to be a comma-separated list. QUESTION FOR HAML FORMAT: What do we do when there are multiple shared specificities for a bead?


        self.determineFormatAndManufacturer()
        print('Done Determining File Format. delimiter=(' + str(self.delimiter) + ') allFieldsQuoted=(' + str(self.allFieldsQuoted) + ') manufacturer=(' + str(self.manufacturer) + ')')

        pandasCsvReader = readCsvFile(csvFileName=self.csvFileName, delimiter=self.delimiter, allFieldsQuoted=self.allFieldsQuoted)

        if(self.delimiter is None or self.allFieldsQuoted is None or self.manufacturer is None):
            self.validationFeedback=('Could not determine the format of the input File!\nSomething is strange about the csv file:\n'
                + 'delimiter=(' + str(self.delimiter) + ')\nallFieldsQuoted=(' + str(self.allFieldsQuoted) + ')\nmanufacturer=(' + str(self.manufacturer) + ')')
        elif self.manufacturer == 'OneLambda':
            self.validationFeedback=self.ProcessOneLambda(pandasCsvReader=pandasCsvReader)
        elif self.manufacturer == 'Immucor':
            self.validationFeedback=self.ProcessImmucor(pandasCsvReader=pandasCsvReader)
        else:
            print('Not known manufacturer, unable to convert file')
            return False

def readCsvFile(csvFileName=None, delimiter=None, allFieldsQuoted=False):
    #print('Reading csv File:' + str(csvFileName))

    # Copying the file is necessary to work on S3 environment.
    # Copy the file object so we don't use up the buffer. This is important when it's reading from S3 streams.
    copyInputFile = copy.deepcopy(csvFileName)

    # TODO: index_col=False ? That option was used in some cases, is it necessary?
    try:
        if(allFieldsQuoted):
            # this seems to work for one lambda files
            #print('Opening file with every quoted field:')
            pandasCsvReader = pd.read_csv(copyInputFile, sep=delimiter, quoting=csv.QUOTE_ALL)

        else:
            #print('Opening file, undefined quote behavior.')
            pandasCsvReader = pd.read_csv(copyInputFile, sep=delimiter, engine="python")

        pandasCsvReader = pandasCsvReader.loc[:,~pandasCsvReader.columns.str.contains('^Unnamed')]  # eliminate empty columns at the end

        pandasCsvReader.rename(columns=lambda x: x.replace(' ',''), inplace=True)
        pandasCsvReader.rename(columns=lambda x: x.replace('/','_'), inplace=True)

        return pandasCsvReader

    except Exception as e:
        print('Exception when reading csv file ' + str(csvFileName) + ' : ' + str(e))
        raise(e)

# This is a helper function helping format the tags into separate subElements instead of attributes
def makeSubElement(parent, tag, extra=None):
    SE = ET.SubElement(parent, tag)
    if (extra is None):
        return SE
    else:
        for element in extra:
            SSE = ET.SubElement(SE, element)
            SSE.text = extra[element]
        return SE

def parseArgs():
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--csv", help="xml file to validate", type=str, required=True)
    parser.add_argument("-x", "--xml", help="xml(haml) file to write output to.", type=str, required=True)
    parser.add_argument("-l", "--lab", help="lab identifier", type=str, required=False)

    return parser.parse_args()


if __name__ == '__main__':

    args = parseArgs()
    csvFile = args.csv
    xmlFile = args.xml
    try:
        labID = args.lab
    except Exception as e:
        labID = "Unavailable"

    print('csvFile:' + csvFile)
    print('xmlFile:' + str(xmlFile))

    converter = Converter(csvFileName=csvFile, manufacturer=None, xmlFile=xmlFile, labID=labID)
    converter.convert()

    print('Validation Feedback:' + str(converter.validationFeedback))


    print('Done. Results written to ' + str(xmlFile))