rem Run SEC Edgar Filer Manual (EFM) Conformance Suite tests

@set TESTCASESROOT=C:\Users\Herm Fischer\Documents\mvsl\projects\SEC\Local.Conformance\conformance\Private\Formula\Extension-Conformance\root\efm-18-111004\conf

@set TESTCASESINDEXFILE=%TESTCASESROOT%\testcases.xml

@set OUTPUTLOGFILE=c:\temp\EFM-test-log.txt

@set OUTPUTERRFILE=c:\temp\EFM-test-err.txt

@set OUTPUTCSVFILE=c:\temp\EFM-test-report.csv

@set ARELLEDIR=C:\Users\Herm Fischer\Documents\mvsl\projects\Arelle\ArelleProject\arelle

@set PYTHONDIR=c:\python31
@set PYTHONPATH=..

"%PYTHONDIR%\python" -m arelle.CntlrCmdLine --file "%TESTCASESINDEXFILE%" --efm --utr --validate --csvTestReport "%OUTPUTCSVFILE%" --logFile "%OUTPUTLOGFILE%" 2>  "%OUTPUTERRFILE%"
