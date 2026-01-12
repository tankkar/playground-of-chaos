import os
from FastHPOCR.IndexHPO import IndexHPO
from FastHPOCR.HPOAnnotator import HPOAnnotator
indexConfig = {
    'rootConcepts': [],  
    'allow3LetterAcronyms': True,      
    'includeTopLevelCategory': False,  
    'allowDuplicateEntries': False     
}

hpoFileLocation = "hp.obo"

outputFolder = "hpo_index"
outputIndexFile = os.path.join(outputFolder, "hp_full.index")  

if not os.path.exists(outputFolder):
    os.makedirs(outputFolder)

indexHPO = IndexHPO(hpoFileLocation, outputFolder, indexConfig=indexConfig)
indexHPO.index()
print("Full HPO index built at:", os.path.join(outputFolder, "hp.index"))