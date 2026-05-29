import requests, time
BASE='http://127.0.0.1:8000/api'
email=f'fe_test_{int(time.time())}@example.com'
payload={'email':email,'password':'Testpass123!','full_name':'FE Test'}
r=requests.post(BASE+'/auth/register', json=payload, headers={'Origin':'http://localhost:3002'})
print('Status', r.status_code)
print('Headers', r.headers.get('access-control-allow-origin'))
print('Text', r.text)
