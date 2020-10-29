class User:
    '''
    securiCAD's user.
    '''

    def __init__(self, name, password, organization=None, role=None):
        # if role in ['user', 'system admin', 'admin', 'project creator']:
        #     self.role = role
        # else:
        #     print("Role of the user is expected to be one of 'user', 'admin' and 'project creator'.")
        #     return
        self.name = name
        self.password = password
        if organization is None:
            self.organization = ''
        else:
            self.organization = organization
