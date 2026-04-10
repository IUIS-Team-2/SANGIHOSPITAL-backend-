# backend/patients/templates.py

DISCHARGE_TEMPLATES = {
    "NORMAL": {
        "title": "DISCHARGE SUMMARY",
        "sections": {
            "final_diagnosis": {"label": "FINAL DIAGNOSIS :", "type": "textarea", "value": ""},
            "chief_complaints": {"label": "CHIEF COMPLAINTS/REASON FOR ADMISSION :", "type": "textarea", "value": "Patient came/presented in hospital with complaints of - "},
            "k_c_o": {"label": "K/C/O :", "type": "textarea", "value": ""},
            "clinical_examination": {
                "label": "CLINICAL EXAMINATION :",
                "type": "vitals_grid",
                "value": {"bp": "", "pulse": "", "spo2": "", "temp": "", "chest": "B/L Wheeze+", "cvs": "S1S2+", "cns": "Conscious/Restlessness", "abd": "Soft"}
            },
            "operations_procedures": {"label": "OPERATIONS/PROCEDURES DONE :", "type": "textarea", "value": "None"},
            "course_in_hospital": {
                "label": "COURSE IN HOSPITAL/CASE SUMMARY :",
                "type": "textarea",
                "value": "Patient was admitted with above mentioned complaints. After initial treatment patient shifted to ICU & treatment started with O2 support and managed with IV Fluids, IV antibiotic’s, IV antipyretic’s, IV Bronchodilators, IV PPI and with other supportive & symptomatic treatment. \n\nAll relevant radiological and pathological investigations sent immediately. Patient general condition improved, Patient can manage O2 saturation without O2 support. Patient is being discharged with oral medicine."
            },
            "investigations": {"label": "INVESTIGATIONS :", "type": "textarea", "value": "All investigation is enclosed."},
            "condition_at_discharge": {"label": "CONDITION AT DISCHARGE :", "type": "text", "value": "Fair & Stable."},
            "next_appointment": {"label": "NEXT APPOINTMENT :", "type": "text", "value": "R/W after 5 days"},
            "treatment_advised": {"label": "TREATMENT ADVISED :", "type": "textarea", "value": ""}
        }
    },
    
    "LAMA": {
        "title": "LAMA SUMMARY",
        "sections": {
            "final_diagnosis": {"label": "FINAL DIAGNOSIS :", "type": "textarea", "value": ""},
            "chief_complaints": {"label": "CHIEF COMPLAINTS/REASON FOR ADMISSION :", "type": "textarea", "value": "Patient came/presented in hospital with complaints of - "},
            "k_c_o": {"label": "K/C/O :", "type": "textarea", "value": ""},
            "clinical_examination": {
                "label": "CLINICAL EXAMINATION :",
                "type": "vitals_grid",
                "value": {"bp": "", "pulse": "", "spo2": "", "temp": "", "chest": "B/L Crepts+", "cvs": "S1S2+", "cns": "Conscious/Restlessness", "abd": "Tenderness+", "pallor": "Pallor+", "icterus": "Icterus+"}
            },
            "operations_procedures": {"label": "OPERATIONS/PROCEDURES DONE :", "type": "textarea", "value": "None"},
            "course_in_hospital": {
                "label": "COURSE IN HOSPITAL/CASE SUMMARY :",
                "type": "textarea",
                "value": "Patient was admitted with above mentioned complaints. After initial treatment patient shifted to ICU & treatment started with O2 support and managed with IV Fluids, IV antibiotic’s, IV antipyretic’s, IV Bronchodilators, IV PPI and with other supportive & symptomatic treatment. \n\nPatient general condition improved, but attenders don’t want to continue the treatment and wants discharge, So Patient is discharged as LAMA (Leave Against Medical Advice). Risk and Prognosis Explained to Attenders."
            },
            "investigations": {"label": "INVESTIGATIONS :", "type": "textarea", "value": "All investigation is enclosed."},
            "condition_at_discharge": {"label": "CONDITION AT DISCHARGE :", "type": "text", "value": "LAMA."}
        }
    },
    
    "REFER": {
        "title": "REFER SUMMARY",
        "sections": {
            "final_diagnosis": {"label": "FINAL DIAGNOSIS :", "type": "textarea", "value": ""},
            "chief_complaints": {"label": "CHIEF COMPLAINTS/REASON FOR ADMISSION :", "type": "textarea", "value": "Patient came/presented in hospital with complaints of - "},
            "k_c_o": {"label": "K/C/O :", "type": "textarea", "value": ""},
            "clinical_examination": {
                "label": "CLINICAL EXAMINATION :",
                "type": "vitals_grid",
                "value": {"bp": "", "pulse": "", "spo2": "", "temp": "", "chest": "B/L Rhonchi+", "cvs": "S1S2+", "cns": "Conscious/Restlessness", "abd": "Soft"}
            },
            "operations_procedures": {"label": "OPERATIONS/PROCEDURES DONE :", "type": "textarea", "value": "None"},
            "course_in_hospital": {
                "label": "COURSE IN HOSPITAL/CASE SUMMARY :",
                "type": "textarea",
                "value": "Patient was admitted with above mentioned complaints. After initial treatment patient shifted to ICU & treatment started with O2 support and managed with IV Fluids, IV antibiotic’s, IV antipyretic’s, IV Bronchodilators, IV PPI and with other supportive & symptomatic treatment. \n\nPatient is referred to higher medical centre for further evaluation & management."
            },
            "investigations": {"label": "INVESTIGATIONS :", "type": "textarea", "value": "All investigation is enclosed."},
            "condition_at_discharge": {"label": "CONDITION AT DISCHARGE :", "type": "text", "value": "REFER."}
        }
    },
    
    "DOPR": {
        "title": "DOPR SUMMARY",
        "sections": {
            "final_diagnosis": {"label": "FINAL DIAGNOSIS :", "type": "textarea", "value": ""},
            "chief_complaints": {"label": "CHIEF COMPLAINTS/REASON FOR ADMISSION :", "type": "textarea", "value": "Patient came/presented in hospital with complaints of - "},
            "clinical_examination": {
                "label": "CLINICAL EXAMINATION :",
                "type": "vitals_grid",
                "value": {"bp": "", "pulse": "", "spo2": "", "temp": "", "chest": "B/L Crepts+", "cvs": "S1S2+", "cns": "Conscious/Restlessness", "abd": "Tenderness+", "pallor": "Pallor++", "icterus": "Icterus+++"}
            },
            "operations_procedures": {"label": "OPERATIONS/PROCEDURES DONE :", "type": "textarea", "value": "None"},
            "course_in_hospital": {
                "label": "COURSE IN HOSPITAL/CASE SUMMARY :",
                "type": "textarea",
                "value": "Patient was admitted with above mentioned complaints. After initial treatment patient shifted to ICU & treatment started with O2 support and managed with IV Fluids, IV antibiotic’s, IV antipyretic’s, IV Bronchodilators, IV PPI and with other supportive & symptomatic treatment. \n\nPatient need hospitalization for some more days to recover but Patient’s attenders requesting for discharge, So patient is discharge as DOPR with oral medicine."
            },
            "investigations": {"label": "INVESTIGATIONS :", "type": "textarea", "value": "All investigation is enclosed."},
            "condition_at_discharge": {"label": "CONDITION AT DISCHARGE :", "type": "text", "value": "DOPR."},
            "next_appointment": {"label": "NEXT APPOINTMENT :", "type": "text", "value": "R/W after 5 days"},
            "treatment_advised": {"label": "TREATMENT ADVISED :", "type": "textarea", "value": ""}
        }
    },

    "DEATH": {
        "title": "DEATH SUMMARY",
        "sections": {
            "final_diagnosis": {"label": "FINAL DIAGNOSIS :", "type": "textarea", "value": ""},
            "chief_complaints": {"label": "CHIEF COMPLAINTS/REASON FOR ADMISSION :", "type": "textarea", "value": "Patient came/presented in hospital with complaints of - "},
            "k_c_o": {"label": "K/C/O :", "type": "textarea", "value": ""},
            "clinical_examination": {
                "label": "CLINICAL EXAMINATION :",
                "type": "vitals_grid",
                "value": {"bp": "", "pulse": "", "spo2": "", "temp": "", "chest": "B/L Wheeze+", "cvs": "S1S2+", "cns": "Conscious/Restlessness", "abd": "Soft"}
            },
            "operations_procedures": {"label": "OPERATIONS/PROCEDURES DONE :", "type": "textarea", "value": "None"},
            "course_in_hospital": {
                "label": "COURSE IN HOSPITAL/CASE SUMMARY :",
                "type": "textarea",
                "value": "Patient was admitted with above mentioned complaints. After initial treatment patient shifted to ICU & treatment started with O2 support and managed with IV Fluids, IV antibiotic’s, IV antipyretic’s, IV Bronchodilators, IV PPI and with other supportive & symptomatic treatment. \n\nPatient’s General Condition become deteriorated & Patient was unable to maintain SPO2 saturation even with O2 Support. CPR was started with all life saving drugs. CPR was continued but patient not revived ECG shows Straight Line & Pupils are Fixed & Dialated & Patient is declared Dead."
            },
            "investigations": {"label": "INVESTIGATIONS :", "type": "textarea", "value": "All investigation is enclosed."},
            "condition_at_discharge": {"label": "CONDITION AT DISCHARGE :", "type": "text", "value": "DEATH."}
        }
    }
}