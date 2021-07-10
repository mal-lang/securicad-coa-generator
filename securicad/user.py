# Copyright 2020-2021 Wojciech Wideł <widel@kth.se>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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
