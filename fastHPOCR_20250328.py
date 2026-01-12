import os
from FastHPOCR.IndexHPO import IndexHPO
from FastHPOCR.HPOAnnotator import HPOAnnotator
# Optional index configuration (adjust as needed)
indexConfig = {
    'rootConcepts': ['HP:0000001'],
    'allow3LetterAcronyms': True,  # set to True if you want to include them
    'includeTopLevelCategory': True,      # adds extra concept info if available
    'allowDuplicateEntries': True        # change to True to allow duplicates
}

hpoFileLocation = "hp.obo"

outputFolder = "hpo_index2"
if not os.path.exists(outputFolder):
    os.makedirs(outputFolder)

#indexHPO = IndexHPO(hpoFileLocation, outputFolder, indexConfig=indexConfig)
#indexHPO.index()
print("Indexing complete. Index stored in:", outputFolder)


###################input email text#################
import os
from FastHPOCR.HPOAnnotator import HPOAnnotator

# Specify the folder where the index was stored
outputFolder = "hpo_index2"
# Construct the full path to the index file
index_file_path = os.path.join(outputFolder, "hp.index")

# Initialize the HPOAnnotator with the index file, not the folder
hpoAnnotator = HPOAnnotator(index_file_path)

# Sample email text
email_text = """
n HN251609217
Gestation on admission: 37+6 weeks
Antenatal complication: GBS positive, IUGR, unfavourable cervix
Admitted for cervical assessment for IUGR. induction of labour for IUGR.
SVD
Intrapartum/ postnatal complication: nil

[Maternal Discharge Summary]
Gravida: 1
Parity: 1
Maturity: 38 weeks 0 days
Date of Delivery: 15-Dec-2025 22:23:00
Antenatal Complications: Nil
Blood Group: Blood group B
Rhesus: +ve
Rubella Antibody: Rubella-immune
HBSAg: Hepatitis Antigen -ve
VDRL: VDRL -ve
Postnatal Complications: Nil
Follow Up:
1) mch
<Baby>
UM Number: UM4547033
Birth Order: 1
Birth Datetime: 15/12/2025 22:23
Birth Weight (gm): 2535
Sex: F
Apgar scores: 9(1) 10(5) (10)
Mode of Delivery:
1) Normal spontaneous delivery
I delivered my little girl, Sophelia, on Dec 15 night 10:23pm (38wk+1, induction due to IUGR, BW 2.53kg, uneventful delivery process). She’s well during the first 24 hours, but became irritable and had borderline Spo2 on Dec 16 night. She’s started on empirical ampicillin and gentamicin (as I’m GBS positive and given one dose antibiotics only due to fast delivery after amniotic sac rupture). The WCC & repeated CRP were within normal range. LP (traumatic tap) not suggestive of meningitis. USG brain NAD, will have it repeated next week. During stay at SBCU, she’s noted to have frequent periodic breathing (with desat down to 70s occasionally) and transferred to neonatal ICU. She’s now on CPAP support and caffeine citrate since Dec 18. Dr Mabel Wong has been taking care of her and she would approach you tomorrow for rapid genetic testing (me and my husband are available anytime) as the cause is still under workup. Thank you very much!!
"""

# Extract HPO annotations from the email text
annotations = hpoAnnotator.annotate(email_text)
print("Extracted Annotations:")
print(annotations)

# Optionally, serialize the annotations to a file
outputAnnotationFile = "annotations.json"
hpoAnnotator.serialize(annotations, outputAnnotationFile, includeCategoriesIfPresent=True)
print("Annotations saved to", outputAnnotationFile)
