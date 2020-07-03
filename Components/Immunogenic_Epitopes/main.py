from sys import exc_info
import argparse
import io

from ImmunogenicEpitopes import validateEpitopesDataMatrix

try:
    from IhiwRestAccess import setValidationStatus
    from S3_Access import writeFileToS3
    from ParseExcel import createBytestreamExcelOutputFile, parseExcelFile, getColumnNumberAsString, createExcelValidationReport
except Exception:
    from Common.IhiwRestAccess import setValidationStatus
    from Common.S3_Access import writeFileToS3
    from Common.ParseExcel import createBytestreamExcelOutputFile, parseExcelFile, getColumnNumberAsString, createExcelValidationReport

def parseArgs():
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--validator", required=True, help="validator type", type=str)
    parser.add_argument("-ex", "--excel", required=False, help="input excel file", type=str)
    parser.add_argument("-up", "--upload", required=False, help="upload file name", type=str)
    parser.add_argument("-b", "--bucket", required=False, help="S3 Bucket Name", type=str )

    return parser.parse_args()

def testValidateImmunogenicEpitopes(excelFile=None):
    print('Starting up the immuno epitopes methods.')

    validationResults = validateEpitopesDataMatrix(excelFile=excelFile, isImmunogenic=True)
    print('Validation Results:\n' + str(validationResults))

def testValidateNonImmunogenicEpitopes(excelFile=None):
    print('Starting up the non immunogenic epitopes methods.')

    validationResults = validateEpitopesDataMatrix(excelFile=excelFile, isImmunogenic=False)
    print('Validation Results:\n' + str(validationResults))

def testSetValidationResults(args=None):
    uploadFileName = args.upload
    isValid = False
    validationFeedback = ('In data column hml_id_donor I could not find an uploaded file with the name (2_1590401697183_HML_good.hml.1.0.1.xml); ' +
        'In data column hml_id_recipient I could not find an uploaded file with the name (fake.hml); ' +
        'In data column haml_id_recipient_pre_tx I could not find an uploaded file with the name (2_1590401779132_HAML_HamlFromNewConverter.xml); ' +
        'In data column haml_id_recipient_post_tx I could not find an uploaded file with the name (2_1590401779132_HAML_HamlFromNewConverter.xml); ' +
        'In data column hml_id_donor I could not find an uploaded file with the name (2_1590401697183_HML_good.hml.1.0.1.xml); ' +
        'In data column hml_id_recipient For file entry (good.hml.1.0.1.hml), 2 matching files were found:(1497_1589832668946_HML_good.hml.1.0.1.hml) , (1497_1590413494993_HML_good.hml.1.0.1.hml) ,; ' +
        'In data column haml_id_recipient_pre_tx I could not find an uploaded file with the name (2_1590401816855_HAML_HLAM_Fusion.csv); ' +
        'In data column haml_id_recipient_post_tx I could not find an uploaded file with the name (2_1590401779132_HAML_HamlFromNewConverter.xml); ' +
        'In data column hml_id_donor I could not find an uploaded file with the name (2_1590401697183_HML_good.hml.1.0.1.xml); ' +
        'In data column hml_id_recipient I could not find an uploaded file with the name (2_1590401697183_HML_good.hml.1.0.1.xml); ' +
        'In data column haml_id_recipient_pre_tx I could not find an uploaded file with the name (2_1590401816855_HAML_HLAM_Fusion.csv); ' +
        'In data column haml_id_recipient_post_tx I could not find an uploaded file with the name (2_1590401816855_HAML_HLAM_Fusion.csv); ' +
        'In data column hml_id_donor I could not find an uploaded file with the name (2_1590401697183_HML_good.hml.1.0.1.xml); ' +
        'In data column hml_id_recipient I could not find an uploaded file with the name (2_1590401697183_HML_good.hml.1.0.1.xml); ' +
        'In data column haml_id_recipient_pre_tx I could not find an uploaded file with the name (2_1590401816855_HAML_HLAM_Fusion.csv.haml); ' +
        'In data column haml_id_recipient_post_tx I could not find an uploaded file with the name (2_1590401816855_HAML_HLAM_Fusion.csv); ')
    validatorType='IMMUNOGENIC_EPITOPES'
    validationResult = setValidationStatus(uploadFileName=uploadFileName, isValid=isValid, validationFeedback=validationFeedback, validatorType=validatorType)
    #print('ValidationResult=' + str(validationResult))

    if (validationResult):
        print('Validation status for uploadFileName' + str(uploadFileName) + ' was set successfully to ' + str(isValid) + '.')
    else:
        print('FAILED to set validation status!')

def testWriteFileS3(args=None):
    print('Opening Input Workbook...')
    excelFile=args.excel
    inputWorkbookData = parseExcelFile(excelFile=excelFile)
    if(inputWorkbookData is None or len(inputWorkbookData) < 1):
        print('I failed to open the input workbook data. Cannot continue.')
        return None
    else:
        pass
        print('Workbook was opened, this is the data:' + str(inputWorkbookData))

    # Some test errors. The column headers with errors are stored for each line
    errors = [{'prozone_post_tx':'This cell is missing data'},{'availability_pre_tx':'File is wrong format or whatever.'}]

    # Create output files
    outputWorkbook, outputWorkbookbyteStream = createExcelValidationReport(errors=errors, inputWorkbookData=inputWorkbookData)

    # Write the Excel File to S3 storage.
    writeFileToS3(newFileName=args.upload, bucket=args.bucket, s3ObjectBytestream=outputWorkbookbyteStream)





if __name__=='__main__':
    try:
        args=parseArgs()
        validatorType =args.validator
        if(validatorType=='IMMUNOGENIC_EPITOPES'):
            testValidateImmunogenicEpitopes(excelFile=args.excel)
        elif(validatorType=='NON_IMMUNOGENIC_EPITOPES'):
            testValidateNonImmunogenicEpitopes(excelFile=args.excel)
        elif(validatorType=='SET_VALIDATION_RESULTS'):
            testSetValidationResults(args=args)
        elif(validatorType=='WRITE_FILE_S3'):
            testWriteFileS3(args=args)
        else:
            print('I do not understand the validator type.')


    except Exception:
        print ('Unexpected problem running tests:')
        print (str(exc_info()))
        raise
