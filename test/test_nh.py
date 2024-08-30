import requests

url = "https://aan.nhdmp.com/track"
headers = {
    "accept": "*/*",
    "content-type": "application/x-www-form-urlencoded; charset=utf-8",
    "accept-charset": "UTF-8",
    "accept-encoding": "gzip, deflate, br",
    "user-agent": "MoleculeTracker SDK URLSessionDispatcher",
    "accept-language": "ko-KR,ko;q=0.9"
}

payload = {
    "parameters": '{"pav":"[5326] FICC : X08m5324","prd":"iPhone16,1","eva":"","pcv":"FICC","ist":"","sst":"1720626306082","av":"[5331] 배류파인더 탐방노트 : X08m5332","itl":"","mfr":"apple","rct":"-1","rrf":"","cv":"배류파인더 탐방노트","aid":"30BE6D15-5743-4E3E-A34F-A8BA57EF774C","oid":"i_30BE6D1557434E3EA34FA8BA57EF774C","ini":"false","ip6":"FE80::9D:EBAD:2E97:D1C","ifv":"30BE6D15-5743-4E3E-A34F-A8BA57EF774C","ti":"1720626617186","ty":"pv","evc":"","ip4":"192.168.1.184","evl":"","ctr":"KR","rs":"393x852","set":"1720628417186","mid":"AA-1014","ity":"","sdt":"311104","sid":"i_30BE6D1557434E3EA34FA8BA57EF774C_1720626306082","sch":"","nt":"WIFI","irf":"","tcid":"","mdl":"iPhone16,1","tid":"","turi":"https:\/\/nhqv.com\/openscreen?scrno=5331","exa":"","mky":"7rNpc18d","fit":"1720000086946","cr":"--","apv":"12.19","ibt":"-1","ln":"ko","brd":"apple","pkn":"","osv":"17.5.1","sdv":"u_2.1.6.P","lut":"-1","usa":""}'
}

response = requests.post(url, headers=headers, data=payload)

print(response.status_code)
print(response.text)