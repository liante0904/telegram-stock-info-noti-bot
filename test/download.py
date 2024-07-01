import wget

url = "https://rcv.kbsec.com/streamdocs/pdfview?id=B520190322125512762443&url=aHR0cDovL3JkYXRhLmtic2VjLmNvbS9wZGZfZGF0YS8yMDI0MDYxNDE1MzcyNTY2MEsucGRm"
wget.download(url,'파일명테스트.pdf')
	# url = 'https://www.hmsec.com/documents/research/20240613163747237_ko.pdf'
	# download(url)