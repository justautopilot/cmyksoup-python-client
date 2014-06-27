import json, requests, hmac, decimal, config
from hashlib import sha1

def dthandler(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, Decimal):
        return str(obj)
    else:
        try:
            return json.JSONEncoder().default(obj)
        except:
            return str(obj)

def sanitize(params, whitelist, additions):
    params=filter_params(params, whitelist)
    for k,v in additions.iteritems():
        params[k]=v
    return params

def filter_params(params, whitelist):
    return dict([(k,v) for k,v in params.iteritems() if k in whitelist ])

class Serializable(object):
    """SQLAlchemy Model JSON Serializable

    A class to help serialize sqlalchemy models
    in JSON format
    """
    __exclude_from_json__ = []

    def to_serializable_dict(self):
        data = {}
        for key in self.__table__.columns.keys():
            data[key] = getattr(self, key)

        for key in self.__mapper__.relationships.keys():
            if key not in self.__exclude_from_json__:
                if self.__mapper__.relationships[key].uselist:
                    data[key] = []
                    for item in getattr(self, key):
                        data[key].append(item.to_serializable_dict())
                else:
                    data[key] = getattr(self, key)

        return data

    def to_json(self):
        return json.dumps(self.to_serializable_dict(), default=dthandler)



def get_signature(secret_key, request=None, message=None):
    """Generate signature

    Method to sign a http request using HMAC
    """
    if request:
        message = request.path + request.method + request.headers['Content-Type']
    signature = hmac.new(secret_key, message, sha1)
    return signature.hexdigest()


def send_request(method, path, payload=None):
    #print "sending request to %s with payload %s" % (path, str(payload))
    url = config.API_BASE_URL + path
    message = path + method + "application/json"
    headers = {
        'Content-Type': 'application/json',
        'Authorization': "%s:%s" % (config.API_KEY,
                                    get_signature(str(config.API_SECRET_ACCESS_KEY),
                                                  message=message))
    }
    if method=="POST":
      res = requests.post(url, data=json.dumps(payload), headers=headers)
    elif method=="GET":
      if payload:
        res = requests.get(url, headers=headers, params=payload )
      else:
        res = requests.get(url, headers=headers )
    elif method=="PUT":
      res = requests.put(url, data=json.dumps(payload), headers=headers)
    elif method=="DELETE":
      res = requests.delete(url, headers=headers)
    else:
      res=None
    return res


def ping():
    return send_request('GET','/').json()

class Merchandise:

    def __init__(self, category, id, name=None, private_label=None, tshirt_type=None, color=None, dimension=None, dimension_unit=None ):
        self.category=category
        self.id=id
        self.name=name
        if self.category  == 'tshirt':
            self.private_label= (int(private_label)!=0 )
            self.tshirt_type = tshirt_type
            self.color = color
        elif self.category =='sticker' or self.category == 'sticker_sheet':
            self.dimension=dimension
            self.dimension_unit=dimension_unit

    def __repr__(self):
        return  "%s - %s"%(self.category.capitalize().replace('_',' '), self.name)

    @staticmethod
    def _filter_params(merch):
        return filter_params(merch, ('id','category','name','private_label','tshirt_type','dimension','dimension_unit', 'color'))

    @staticmethod
    def all():
        response = send_request('GET', '/v1/merchandise')
        res=response.json()
        if response.status_code==200 and res['status']=='success':
            return [ Merchandise(**Merchandise._filter_params(merch) ) for merch in res['merchandise'] ]
        else:
            return []

      

    def skus(self, **params):
        response = send_request('GET', '/v1/merchandise/%s/skus'%self.id, params)
        if response.status_code==200:
            result=response.json()
            if result['status']=='success':
                return [ SKU(**SKU._filter_params(item) ) for item in result['skus'] ]
        return []

    def sku(self, **params):
        params['one']=True
        response = send_request('GET', '/v1/merchandise/%s/skus'%self.id, params)
        if response.status_code==200:
            result=response.json()
            if result['status']=='success':
                return SKU(**SKU._filter_params(result['sku']) )
        return None

    @staticmethod
    def get(id):
        response = send_request('GET', '/v1/merchandise/%s'%id)
        res=response.json()
        if response.status_code==200 and res['status']=='success':
            return Merchandise(**Merchandise._filter_params(res['merchandise']) )
        else:
            return None


class SKU:

    def __init__(self, id, category, available_stock, merchandise_name=None, merchandise_id=None,  color=None, size=None,
                    tshirt_type=None, translucent=None, name=None, dimension=None, dimension_unit=None  ):
        self.id=id
        self.category=category
        self.available_stock=available_stock
        if self.category!='sku':
            self.merchandise_name=merchandise_name
            self.merchandise_id=merchandise_id
        if self.category=='tshirt_merchandise':
            self.color=color
            self.size=size
            self.tshirt_type=tshirt_type
        if self.category=='sticker_merchandise' or self.category=='sticker_sheet_merchandise':
            self.translucent=(int(translucent)!=0)
        if self.category=='sticker_merchandise' or self.category=='sticker_sheet_merchandise' or self.category=='postcard_merchandise':
            self.dimension=dimension
            self.dimension_unit=dimension_unit
        if self.category=='sku':
            self.name=name


    @staticmethod
    def _filter_params(sku):
        return filter_params(sku, ('id','category','available_stock','merchandise_name','merchandise_id',
                            'color','size', 'tshirt_type','translucent', 'name', 'dimension', 'dimension_unit'))

   

    @staticmethod
    def all():
        response = send_request('GET', '/v1/skus')
        if response.status_code==200:
            result=response.json()
            if result['status']=='success':
                return [ SKU(**SKU._filter_params(item) ) for item in result['skus'] ]
        return []

    @staticmethod
    def get(id):
        response = send_request('GET', '/v1/skus/%s'%id)
        if response.status_code==200:
            result=response.json()
            if result['status']=='success':
                return SKU(**SKU._filter_params(result['sku']) ) 
        return None  

    def __repr__(self):
        return self.id 


class Recipient:

    def __init__(self, id, name, email, address1,  city, state, country, pincode,contact_number=None, address2=None ):
        self.id=id
        self.name = name
        self.email = email
        self.address1 = address1
        self.address2 = address2
        self.city = city
        self.state = state
        self.country = country
        self.pincode=pincode
        self.contact_number=contact_number

    @staticmethod
    def _filter_params(shipment):
        return filter_params(shipment, ('id','name','email','address1','address2','city','state', 'country', 'pincode', 'contact_number'))

    @staticmethod
    def all():
        response = send_request('GET', '/v1/recipients')
        if response.status_code==200:
            result=response.json()
            if result['status']=='success':
                return [ Recipient(**Recipient._filter_params(item) ) for item in result['recipients'] ]
        return []

    @staticmethod
    def get(id):
        response = send_request('GET', '/v1/recipients/%s'%id)
        if response.status_code==200:
            result=response.json()
            if result['status']=='success':
                return Recipient(**Recipient._filter_params(result['recipient']) ) 
        return None 

    def __repr__(self):
        return "%s <%s>"%(self.name, self.email) 

class Shipment:

    def __init__(self, id,  recipient, contents=[], status=None, shipping_charges=0, tax=0,tracking_url=None,net_amount=0,gross_amount=0 ):
        self.id=id
        self.recipient=Recipient(**Recipient._filter_params(recipient) )
        self.status=status
        self.shipping_charges=shipping_charges
        self.net_amount=net_amount
        self.tax=tax
        self.gross_amount=gross_amount
        self.tracking_url=tracking_url
        self.contents=[]
        for item_params in contents:
            self.contents.append( ( SKU(**SKU._filter_params(item_params['stockable']) ), 
                                    item_params['quantity']
                                    )  )

    @staticmethod
    def _filter_params(shipment):
        return filter_params(shipment, ('id','recipient','status','net_amount','tax','gross_amount','tracking_url', 'contents') )

    @staticmethod
    def create(recipient, contents):
        response = send_request('POST','/v1/shipments', {'contents': contents, 'recipient': recipient })
        if response.status_code==200:
            result=response.json()
            if result['status']=='success':
                return Shipment(**Shipment._filter_params(result['shipment'])),{}
            else:
                raise Exception(result['error'])
        return None

    @staticmethod
    def all():
        response = send_request('GET', '/v1/shipments')
        if response.status_code==200:
            result=response.json()
            if result['status']=='success':
                return [ Shipment(**Shipment._filter_params(item) ) for item in result['shipments'] ]
        return []

    @staticmethod
    def get(id):
        response = send_request('GET', '/v1/shipments/%s'%id)
        if response.status_code==200:
            result=response.json()
            if result['status']=='success':
                return Shipment(**Shipment._filter_params(result['shipment']) ) 
        return None        

class GrantForm:

    def __init__(self, id=None, token=None, url=None, is_valid=None, converted=None, expires_on=None, shipment=None, mailed_to=None, choices=None):
        self.id=id
        self.token=token
        self.url=url
        self.is_valid=is_valid
        self.converted=converted
        self.expires_on=expires_on
        self.mailed_to=mailed_to
        if choices:
            self.choices=choices
        if shipment:
            self.shipment=Shipment(**Shipment._filter_params(shipment) ) 

    @staticmethod
    def _filter_params(grantform):
        return filter_params(grantform, ('choices', 'days_till_expiry', 'mailed_to', 'id','token','url','is_valid', 
                    'converted', 'expires_on', 'shipment', 'mailed_to') )


    @staticmethod
    def all():
        response = send_request('GET', '/v1/grantforms')
        if response.status_code==200:
            result=response.json()
            if result['status']=='success':
                return [ GrantForm(**GrantForm._filter_params(item) ) for item in result['grantforms'] ]
        return []

    @staticmethod
    def create(choices=[], days_till_expiry=90):
        sku_id_choices=[]
        for skus,qty in choices:
            sku_ids=[]
            for sk in skus:
                if isinstance(sk, SKU):
                    sku_ids.append(sk.id)
                elif isinstance(sk,str):
                    sku_ids.append(sk)
            sku_id_choices.append( (sku_ids,qty) )
        response = send_request('POST', '/v1/grantforms', {'choices': sku_id_choices, 'days_till_expiry': days_till_expiry })
        if response.status_code==200:
            result=response.json()
            if result['status']=='success':
                return GrantForm(**GrantForm._filter_params(result['grantform']))
            else:
                raise Exception(result['error'])
        return None

    @staticmethod
    def get(id):
        response = send_request('GET', '/v1/grantforms/%s'%id)
        if response.status_code==200:
            result=response.json()
            print result
            if result['status']=='success':
                return GrantForm(**GrantForm._filter_params(result['grantform']) ) 
        return None  


if __name__ == '__main__':
    pass

