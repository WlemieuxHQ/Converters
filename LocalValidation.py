from HAMLConverterPy import ihiw_converter
from XmlValidator import SchemaValidation

def read_file(file_name):
    with open(file_name, 'r') as input_file:
        file_text = input_file.read()
    return file_text

for f in ["HAMLConverterPy/inputcsv/OLSampleCI2025-05-13.csv", 
          "HAMLConverterPy/inputcsv/OLSampleCII2025-05-13.csv"]:
    o = f.replace("inputcsv", "outputhaml").replace(".csv", ".haml")
    converter = ihiw_converter.Converter(csvFileName=f, manufacturer=None, xmlFile=o, labID="Unavailable")
    converter.convert()

    print('Validation Feedback:' + str(converter.validationFeedback))
    print('Done. Results written to ' + str(o))

    if True:
        xmlFile = read_file(file_name=o)
        val = SchemaValidation.validateAgainstSchema(SchemaValidation.getSchemaText("XmlValidator/schema/haml__version_0_4_4.xsd"), xmlFile)
        
        print('Generated schema is ' + str(val))