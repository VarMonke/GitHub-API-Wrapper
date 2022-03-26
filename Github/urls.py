#== urls.py ==#

BASE_URL = 'https://api.github.com'


#== user urls ==#
USERS_URL = BASE_URL + '/users/{0}'

USER_HTML_URL = 'https://github.com/users/{0}'

SELF_URL = BASE_URL + '/user'

USER_REPOS_URL = USERS_URL + '/repos'

USER_ORGS_URL = USERS_URL + '/orgs'

USER_GISTS_URL = USERS_URL + '/gists'

USER_FOLLOWERS_URL = USERS_URL + '/followers'

USER_FOLLOWING_URL = USERS_URL + '/following'