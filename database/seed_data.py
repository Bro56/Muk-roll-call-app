# -*- coding: utf-8 -*-
"""
Seed data modelling Makerere University's real academic structure:
College -> School -> Department -> Programme -> Course

This is representative, not exhaustive — each department lists a
sample programme with a handful of first-year courses so the app has
real, meaningful data out of the box. Admins can add more via the
Admin Panel (Colleges, Schools, Departments, Programmes, Courses are
all fully manageable in-app).
"""

MAKERERE_STRUCTURE = {
    "College of Computing and Information Sciences (COCIS)": {
        "code": "COCIS",
        "schools": {
            "School of Computing and Informatics Technology (SCIT)": {
                "departments": {
                    "Department of Computer Science": {
                        "programmes": [
                            {
                                "name": "Bachelor of Science in Computer Science",
                                "code": "BSCS",
                                "level": "Bachelors",
                                "courses": [
                                    ("CSC1101", "Introductory Programming", 1, 1),
                                    ("CSC1102", "Data Structures and Algorithms", 1, 2),
                                    ("CSC2102", "Database Systems", 2, 1),
                                    ("CSC2205", "Operating Systems", 2, 2),
                                    ("CSC3111", "Software Engineering", 3, 1),
                                ],
                            }
                        ]
                    },
                    "Department of Information Systems": {
                        "programmes": [
                            {
                                "name": "Bachelor of Science in Information Systems",
                                "code": "BSIS",
                                "level": "Bachelors",
                                "courses": [
                                    ("IS1101", "Fundamentals of Information Systems", 1, 1),
                                    ("IS2101", "Systems Analysis and Design", 2, 1),
                                    ("IS2202", "E-Business Systems", 2, 2),
                                ],
                            }
                        ]
                    },
                    "Department of Information Technology": {
                        "programmes": [
                            {
                                "name": "Bachelor of Information Technology",
                                "code": "BIT",
                                "level": "Bachelors",
                                "courses": [
                                    ("IT1101", "Computer Networks Fundamentals", 1, 1),
                                    ("IT2102", "Web Technologies", 2, 1),
                                    ("IT3105", "Network Administration", 3, 1),
                                ],
                            }
                        ]
                    },
                    "Department of Networks": {
                        "programmes": [
                            {
                                "name": "Bachelor of Science in Networks",
                                "code": "BNET",
                                "level": "Bachelors",
                                "courses": [
                                    ("NET1101", "Introduction to Data Communication", 1, 1),
                                    ("NET2101", "Network Security", 2, 1),
                                ],
                            }
                        ]
                    },
                }
            },
            "East African School of Library and Information Science (EASLIS)": {
                "departments": {
                    "Department of Library and Information Sciences": {
                        "programmes": [
                            {
                                "name": "Bachelor of Library and Information Science",
                                "code": "BLIS",
                                "level": "Bachelors",
                                "courses": [
                                    ("LIS1101", "Foundations of Library Science", 1, 1),
                                    ("LIS2101", "Information Retrieval", 2, 1),
                                ],
                            }
                        ]
                    },
                    "Department of Records and Archives Management": {
                        "programmes": [
                            {
                                "name": "Bachelor of Records and Archives Management",
                                "code": "BRAM",
                                "level": "Bachelors",
                                "courses": [
                                    ("RAM1101", "Introduction to Records Management", 1, 1),
                                ],
                            }
                        ]
                    },
                }
            },
        },
    },
    "College of Engineering, Design, Art and Technology (CEDAT)": {
        "code": "CEDAT",
        "schools": {
            "School of Engineering": {
                "departments": {
                    "Department of Civil and Environmental Engineering": {
                        "programmes": [
                            {
                                "name": "Bachelor of Science in Civil Engineering",
                                "code": "BSCE",
                                "level": "Bachelors",
                                "courses": [
                                    ("CVE1101", "Engineering Mechanics", 1, 1),
                                    ("CVE2101", "Structural Analysis I", 2, 1),
                                ],
                            }
                        ]
                    },
                    "Department of Electrical and Computer Engineering": {
                        "programmes": [
                            {
                                "name": "Bachelor of Science in Electrical Engineering",
                                "code": "BSEE",
                                "level": "Bachelors",
                                "courses": [
                                    ("ELE1101", "Circuit Theory I", 1, 1),
                                    ("ELE2101", "Digital Electronics", 2, 1),
                                ],
                            }
                        ]
                    },
                    "Department of Mechanical Engineering": {
                        "programmes": [
                            {
                                "name": "Bachelor of Science in Mechanical Engineering",
                                "code": "BSME",
                                "level": "Bachelors",
                                "courses": [
                                    ("MEC1101", "Engineering Drawing", 1, 1),
                                    ("MEC2101", "Thermodynamics I", 2, 1),
                                ],
                            }
                        ]
                    },
                }
            },
            "School of the Built Environment": {
                "departments": {
                    "Department of Geomatics and Land Management": {
                        "programmes": [
                            {
                                "name": "Bachelor of Science in Land Surveying",
                                "code": "BSLS",
                                "level": "Bachelors",
                                "courses": [
                                    ("GLM1101", "Principles of Surveying", 1, 1),
                                ],
                            }
                        ]
                    },
                    "Department of Architecture and Physical Planning": {
                        "programmes": [
                            {
                                "name": "Bachelor of Architecture",
                                "code": "BARC",
                                "level": "Bachelors",
                                "courses": [
                                    ("ARC1101", "Architectural Design Studio I", 1, 1),
                                ],
                            }
                        ]
                    },
                }
            },
            "Margaret Trowell School of Industrial and Fine Art (MTSIFA)": {
                "departments": {
                    "Department of Industrial Art and Applied Design": {
                        "programmes": [
                            {
                                "name": "Bachelor of Industrial and Fine Arts",
                                "code": "BIFA",
                                "level": "Bachelors",
                                "courses": [
                                    ("IFA1101", "Drawing and Composition", 1, 1),
                                ],
                            }
                        ]
                    }
                }
            },
        },
    },
    "College of Business and Management Sciences (CoBAMS)": {
        "code": "CoBAMS",
        "schools": {
            "School of Business": {
                "departments": {
                    "Department of Marketing and Management": {
                        "programmes": [
                            {
                                "name": "Bachelor of Commerce",
                                "code": "BCOM",
                                "level": "Bachelors",
                                "courses": [
                                    ("BUS1101", "Principles of Management", 1, 1),
                                    ("BUS2101", "Marketing Management", 2, 1),
                                ],
                            }
                        ]
                    }
                }
            },
            "School of Economics": {
                "departments": {
                    "Department of Economic Theory and Analysis": {
                        "programmes": [
                            {
                                "name": "Bachelor of Economics",
                                "code": "BEC",
                                "level": "Bachelors",
                                "courses": [
                                    ("ECO1101", "Microeconomics I", 1, 1),
                                    ("ECO1102", "Macroeconomics I", 1, 2),
                                ],
                            }
                        ]
                    }
                }
            },
            "School of Statistics and Planning": {
                "departments": {
                    "Department of Statistical Methods and Actuarial Science": {
                        "programmes": [
                            {
                                "name": "Bachelor of Statistics",
                                "code": "BSTAT",
                                "level": "Bachelors",
                                "courses": [
                                    ("STA1101", "Introduction to Probability", 1, 1),
                                ],
                            }
                        ]
                    }
                }
            },
        },
    },
    "College of Health Sciences (CHS)": {
        "code": "CHS",
        "schools": {
            "School of Medicine": {
                "departments": {
                    "Department of Medicine": {
                        "programmes": [
                            {
                                "name": "Bachelor of Medicine and Bachelor of Surgery",
                                "code": "MBChB",
                                "level": "Bachelors",
                                "courses": [
                                    ("MED1101", "Human Anatomy I", 1, 1),
                                    ("MED1102", "Human Physiology I", 1, 2),
                                ],
                            }
                        ]
                    }
                }
            },
            "School of Biomedical Sciences": {
                "departments": {
                    "Department of Biochemistry": {
                        "programmes": [
                            {
                                "name": "Bachelor of Biomedical Sciences",
                                "code": "BBS",
                                "level": "Bachelors",
                                "courses": [
                                    ("BCH1101", "General Biochemistry", 1, 1),
                                ],
                            }
                        ]
                    }
                }
            },
            "School of Public Health": {
                "departments": {
                    "Department of Epidemiology and Biostatistics": {
                        "programmes": [
                            {
                                "name": "Bachelor of Environmental Health Science",
                                "code": "BEHS",
                                "level": "Bachelors",
                                "courses": [
                                    ("PH1101", "Introduction to Public Health", 1, 1),
                                ],
                            }
                        ]
                    }
                }
            },
        },
    },
    "College of Agricultural and Environmental Sciences (CAES)": {
        "code": "CAES",
        "schools": {
            "School of Agricultural Sciences": {
                "departments": {
                    "Department of Agribusiness and Natural Resource Economics": {
                        "programmes": [
                            {
                                "name": "Bachelor of Science in Agribusiness Management",
                                "code": "BSABM",
                                "level": "Bachelors",
                                "courses": [
                                    ("AGE1101", "Principles of Agricultural Economics", 1, 1),
                                ],
                            }
                        ]
                    }
                }
            },
            "School of Forestry, Environmental and Geographical Sciences": {
                "departments": {
                    "Department of Environmental Management": {
                        "programmes": [
                            {
                                "name": "Bachelor of Environmental Science",
                                "code": "BES",
                                "level": "Bachelors",
                                "courses": [
                                    ("ENV1101", "Introduction to Environmental Science", 1, 1),
                                ],
                            }
                        ]
                    }
                }
            },
            "School of Food Technology, Nutrition and Bioengineering": {
                "departments": {
                    "Department of Food Technology and Nutrition": {
                        "programmes": [
                            {
                                "name": "Bachelor of Science in Food Science and Technology",
                                "code": "BFST",
                                "level": "Bachelors",
                                "courses": [
                                    ("FST1101", "Introduction to Food Science", 1, 1),
                                ],
                            }
                        ]
                    }
                }
            },
        },
    },
    "College of Humanities and Social Sciences (CHUSS)": {
        "code": "CHUSS",
        "schools": {
            "School of Liberal and Performing Arts": {
                "departments": {
                    "Department of Literature": {
                        "programmes": [
                            {
                                "name": "Bachelor of Arts",
                                "code": "BA",
                                "level": "Bachelors",
                                "courses": [
                                    ("LIT1101", "Introduction to Literature", 1, 1),
                                ],
                            }
                        ]
                    },
                    "Department of Philosophy": {
                        "programmes": [
                            {
                                "name": "Bachelor of Arts in Philosophy",
                                "code": "BAPH",
                                "level": "Bachelors",
                                "courses": [
                                    ("PHI1101", "Introduction to Philosophy", 1, 1),
                                ],
                            }
                        ]
                    },
                }
            },
            "School of Social Sciences": {
                "departments": {
                    "Department of Sociology and Anthropology": {
                        "programmes": [
                            {
                                "name": "Bachelor of Arts in Social Sciences",
                                "code": "BASS",
                                "level": "Bachelors",
                                "courses": [
                                    ("SOC1101", "Introduction to Sociology", 1, 1),
                                ],
                            }
                        ]
                    }
                }
            },
            "School of Languages, Literature and Communication": {
                "departments": {
                    "Department of Journalism and Communication": {
                        "programmes": [
                            {
                                "name": "Bachelor of Arts in Journalism and Communication",
                                "code": "BAJC",
                                "level": "Bachelors",
                                "courses": [
                                    ("JC1101", "Introduction to Mass Communication", 1, 1),
                                ],
                            }
                        ]
                    }
                }
            },
        },
    },
    "College of Natural Sciences (CoNAS)": {
        "code": "CoNAS",
        "schools": {
            "School of Physical Sciences": {
                "departments": {
                    "Department of Physics": {
                        "programmes": [
                            {
                                "name": "Bachelor of Science (Physics)",
                                "code": "BSCPHY",
                                "level": "Bachelors",
                                "courses": [
                                    ("PHY1101", "Mechanics I", 1, 1),
                                ],
                            }
                        ]
                    },
                    "Department of Chemistry": {
                        "programmes": [
                            {
                                "name": "Bachelor of Science (Chemistry)",
                                "code": "BSCCHEM",
                                "level": "Bachelors",
                                "courses": [
                                    ("CHE1101", "Inorganic Chemistry I", 1, 1),
                                ],
                            }
                        ]
                    },
                    "Department of Mathematics": {
                        "programmes": [
                            {
                                "name": "Bachelor of Science (Mathematics)",
                                "code": "BSCMTH",
                                "level": "Bachelors",
                                "courses": [
                                    ("MTH1101", "Calculus I", 1, 1),
                                ],
                            }
                        ]
                    },
                }
            },
            "School of Biosciences": {
                "departments": {
                    "Department of Plant Sciences, Microbiology and Biotechnology": {
                        "programmes": [
                            {
                                "name": "Bachelor of Science (Biology)",
                                "code": "BSCBIO",
                                "level": "Bachelors",
                                "courses": [
                                    ("BIO1101", "Cell Biology", 1, 1),
                                ],
                            }
                        ]
                    }
                }
            },
        },
    },
    "College of Veterinary Medicine, Animal Resources and Bio-security (COVAB)": {
        "code": "COVAB",
        "schools": {
            "School of Veterinary Medicine and Animal Resources": {
                "departments": {
                    "Department of Veterinary Anatomy": {
                        "programmes": [
                            {
                                "name": "Bachelor of Veterinary Medicine",
                                "code": "BVM",
                                "level": "Bachelors",
                                "courses": [
                                    ("VET1101", "Veterinary Gross Anatomy I", 1, 1),
                                ],
                            }
                        ]
                    },
                    "Department of Veterinary Pharmacy and Clinical Studies": {
                        "programmes": [
                            {
                                "name": "Bachelor of Veterinary Pharmacy",
                                "code": "BVP",
                                "level": "Bachelors",
                                "courses": [
                                    ("VPH1101", "Introduction to Veterinary Pharmacy", 1, 1),
                                ],
                            }
                        ]
                    },
                }
            }
        },
    },
    "College of Education and External Studies (CEES)": {
        "code": "CEES",
        "schools": {
            "School of Education": {
                "departments": {
                    "Department of Foundations and Curriculum Studies": {
                        "programmes": [
                            {
                                "name": "Bachelor of Education (Secondary)",
                                "code": "BEDSEC",
                                "level": "Bachelors",
                                "courses": [
                                    ("EDU1101", "Foundations of Education", 1, 1),
                                ],
                            }
                        ]
                    },
                    "Department of Humanities and Language Education": {
                        "programmes": [
                            {
                                "name": "Bachelor of Education (Arts)",
                                "code": "BEDART",
                                "level": "Bachelors",
                                "courses": [
                                    ("EDL1101", "Language Teaching Methods", 1, 1),
                                ],
                            }
                        ]
                    },
                    "Department of Science, Technology and Vocational Education": {
                        "programmes": [
                            {
                                "name": "Bachelor of Education (Science)",
                                "code": "BEDSCI",
                                "level": "Bachelors",
                                "courses": [
                                    ("EDS1101", "Science Teaching Methods", 1, 1),
                                ],
                            }
                        ]
                    },
                }
            },
            "School of Distance and Lifelong Learning": {
                "departments": {
                    "Department of Open and Distance Learning": {
                        "programmes": [
                            {
                                "name": "Bachelor of Adult and Community Education",
                                "code": "BACE",
                                "level": "Bachelors",
                                "courses": [
                                    ("ODL1101", "Principles of Distance Education", 1, 1),
                                ],
                            }
                        ]
                    }
                }
            },
        },
    },
    "School of Law": {
        "code": "LAW",
        "schools": {
            "School of Law": {
                "departments": {
                    "Department of Public and Comparative Law": {
                        "programmes": [
                            {
                                "name": "Bachelor of Laws",
                                "code": "LLB",
                                "level": "Bachelors",
                                "courses": [
                                    ("LAW1101", "Legal Methods", 1, 1),
                                    ("LAW1102", "Law of Contract I", 1, 2),
                                ],
                            }
                        ]
                    },
                    "Department of Commercial Law": {
                        "programmes": [
                            {
                                "name": "Bachelor of Laws (Commercial Track)",
                                "code": "LLBC",
                                "level": "Bachelors",
                                "courses": [
                                    ("LAW2101", "Company Law", 2, 1),
                                ],
                            }
                        ]
                    },
                }
            }
        },
    },
    "Makerere University Business School (MUBS)": {
        "code": "MUBS",
        "schools": {
            "School of Business Administration": {
                "departments": {
                    "Department of Accounting and Finance": {
                        "programmes": [
                            {
                                "name": "Bachelor of Business Administration",
                                "code": "BBA",
                                "level": "Bachelors",
                                "courses": [
                                    ("ACC1101", "Financial Accounting I", 1, 1),
                                    ("ACC1102", "Principles of Finance", 1, 2),
                                ],
                            }
                        ]
                    },
                    "Department of Procurement and Logistics Management": {
                        "programmes": [
                            {
                                "name": "Bachelor of Procurement and Logistics Management",
                                "code": "BPLM",
                                "level": "Bachelors",
                                "courses": [
                                    ("PLM1101", "Introduction to Procurement", 1, 1),
                                ],
                            }
                        ]
                    },
                }
            }
        },
    },
}
