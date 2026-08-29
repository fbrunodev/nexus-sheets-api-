
class UserInvalidCredentialsException(Exception):
    pass

class UserInactiveAccountException(Exception):
    pass

class UserExpiredPlanException(Exception):
    pass

class UserEmailAlreadyExistsException(Exception):
    pass

class OperatorNotFoundException(Exception):
    pass

class KeyExpiredException(Exception):
    pass

class KeyAlreadyUsedException(Exception):
    pass

class InvalidKeyException(Exception):
    pass


class ActivationKeyGenerationException(Exception):
    pass