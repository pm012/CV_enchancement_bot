


# Telegram Bot asistant for improvement Resume.

The bot uses GenAI API to adjust resume with accordance to Vacancy. It is possible to navigate throughout 4 modes and reset initial data.

State/Workflow diagrams:

<p align="center">
  <img src="./assets/resume-enhancer-state-diagram.svg" alt="App State Diagram" width="700">
</p>




```mermaid
stateDiagram-v2
    [*] --> Start : Launch Application
    
    Start --> UploadData : Load Resume (PDF, DOCX, Text) & Job Description
    
    state "Data Processing" as DataProc {
        UploadData --> SaveCV : Parse & Extract Data
    }
    
    SaveCV --> MainMenu : Context Ready
    
    state "Operational Modes" as Modes {
        MainMenu --> GeneralCVReview : Select Mode 1
        MainMenu --> CoverLetterGen : Select Mode 2
        MainMenu --> LinkedInSummary : Select Mode 3
        MainMenu --> MatchAnalysis : Select Mode 4
        
        GeneralCVReview --> MainMenu : Switch Mode
        CoverLetterGen --> MainMenu : Switch Mode
        LinkedInSummary --> MainMenu : Switch Mode
        MatchAnalysis --> MainMenu : Switch Mode
    }

    state "Global Action" as Global {
        MainMenu --> ResetButton : Press Reset / Upload New
        GeneralCVReview --> ResetButton : Press Reset / Upload New
        CoverLetterGen --> ResetButton : Press Reset / Upload New
        LinkedInSummary --> ResetButton : Press Reset / Upload New
        MatchAnalysis --> ResetButton : Press Reset / Upload New
    }

    ResetButton --> Start : Reset & Upload New Data
```




TBD later: 
1. Profile photo improvement (separate model)
2. Create PDF with adjusted resume
