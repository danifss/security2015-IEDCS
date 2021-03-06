from Crypto.Cipher import PKCS1_v1_5
from Crypto.Hash import SHA
from django.shortcuts import render
from rest_framework import generics
from rest_framework.response import Response
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from core.models import User, Player, Device, Content, Purchase
from core.serializers import *
from CryptoModuleA import *
from SmartCardA import *
import os
import json
import time, datetime
import subprocess


class UserLogin(generics.ListCreateAPIView):
    """<b>User Login</b>"""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    allowed_methods = ['get']

    def get(self, request):
        """
        Gets user id if credentials are correct




        <b>Details</b>

        METHODS : GET



        <b>RETURNS:</b>

        - 200 OK.

        - 400 BAD REQUEST

        - 401 UNAUTHORIZED

        username -- registration username
        password -- registration password
        userCC -- registration CC
        ---
        omit_parameters:
        - form
        """
        if 'password' in request.GET and 'username' in request.GET and 'userCC' in request.GET:
            try:
                user = User.objects.get(username__iexact = request.GET.get('username'))
                # if user.check_password(request.GET.get('password')):
                passwd = request.GET.get('password')
                cc_number = request.GET.get('userCC'
                                            )
                # POST restrictions, removes '+' from url's
                passwd_protected = passwd.replace(" ", "+")

                player = Player.objects.get(user=user)
                crypto = CryptoModule()
                playerIm = getPlayerKey(user, player)
                passwd_plain = crypto.rsaDecipher(playerIm, passwd_protected)
                salt = user.userSalt.decode('base64')
                passwd_hash = CryptoModule.hashingSHA256(passwd_plain, salt)

                #fixpassword = CryptoModule.hashingSHA256(str(passwd), salt)
                
                if passwd_hash == user.password and cc_number == user.userCC:
                    return Response(status=status.HTTP_200_OK) #, data={'id': user.userID, 'first_name': user.firstName,
                                                                     #'last_name': user.lastName, 'email': user.email})
                else:
                    return Response(status=status.HTTP_401_UNAUTHORIZED)
            except Exception as e:
                return Response(status=status.HTTP_401_UNAUTHORIZED)
                # print e
        return Response(status=status.HTTP_400_BAD_REQUEST)


class ContentByUser(generics.ListCreateAPIView):
    """<b>Content by User</b>"""
    queryset = Content.objects.all()
    serializer_class = ContentSerializer
    allowed_methods = ['get']

    def get(self, request, pk=None):
        """
        Gets purchased content by given user id




        <b>Details</b>

        METHODS : GET



        <b>RETURNS:</b>

        - 200 OK.

        ---
        omit_parameters:
        - form
        """
        # print request.META['CSRF_COOKIE']
        try:
            int_id = int(pk)
            user = User.objects.get(userID=int_id)
            purchases = Purchase.objects.all().filter(user=user)
            resp = []
            for p in purchases:
                resp += [p.content]
            self.queryset = resp
        except:
            self.queryset = []
        return self.list(request)


class UserHasContent(generics.ListCreateAPIView):
    """<b>Check if User has Content</b>"""
    queryset = Purchase.objects.all()
    serializer_class = PurchaseSerializer
    allowed_methods = ['get']

    def get(self, request, pk=None):
        """
        Check if given User has any Content




        <b>Details</b>

        METHODS : GET



        <b>RETURNS:</b>

        - 200 OK.

        - 204 NO CONTENT

        ---
        omit_parameters:
        - form
        """
        # print request.META['CSRF_COOKIE']
        try:
            int_id = int(pk)
            user = User.objects.get(userID=int_id)
            purchases = Purchase.objects.all().filter(user=user)
            if len(purchases) > 0:
                return Response(status=status.HTTP_200_OK)
        except:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)


class UserDevice(generics.ListCreateAPIView):
    """<b>Gets User device hash and key</b>"""
    queryset = Device.objects.all()
    serializer_class = DeviceSerializer
    allowed_methods = ['get']

    def get(self, request, pk=None, hash=None):
        """
        Gets device hash and key by given User and Hash




        <b>Details</b>

        METHODS : GET



        <b>RETURNS:</b>

        - 200 OK.

        - 204 NO CONTENT

        ---
        omit_parameters:
        - form
        """
        try:
            int_id = int(pk)
            hash_str = str(hash)
            user = User.objects.get(userID=int_id)
            player = Player.objects.get(user=user)
            device = Device.objects.all().filter(player=player,deviceHash=hash_str)
            if len(device) == 0:
                self.queryset = []
                return Response(status=status.HTTP_204_NO_CONTENT)
            self.queryset = device
        except Exception as e:
            print e
            return Response(status=status.HTTP_204_NO_CONTENT)
        return self.list(request)


class UserDeviceCreate(generics.ListCreateAPIView):
    """<b>Creates new Device</b>"""
    queryset = Device.objects.all()
    serializer_class = DeviceSerializer
    allowed_methods = ['post']

    @csrf_exempt
    def post(self, request):
        """
        Creates a Device




        <b>Details</b>

        METHODS : POST




        <b>Example:</b>


        {

            "hash": "5i9fh938hf83h893hg9384hg9348hg",

            "userID": "1",

            "deviceKey": "982hr834ht348hr3298hr9283hf298hf984ht"

        }



        <b>RETURNS:</b>

        - 200 OK.



        ---
        omit_parameters:
            - form
        """
        # print request.META['CSRF_COOKIE']
        # X-CSRFToken: zhOXQAEtUqXoolDN66tlSJ76zKLPl48N
        # {
        # "hash" : "ola",
        # "userID" : "1",
        # "deviceKey" : "loles"
        # }

        if 'hash' in request.data and 'userID' in request.data and 'deviceKey' in request.data:
            try:
                deviceHash = request.data['hash']
                userID = int(request.data['userID'])
                user = User.objects.get(userID=userID)
                player = Player.objects.get(user=user)
                deviceKey = request.data['deviceKey']
                # create Device and save it
                new_device = Device(deviceKey=deviceKey, player=player, deviceHash=deviceHash)
                new_device.save()
                return Response(status=status.HTTP_200_OK)
            except Exception as e:
                print "Error creating new Device.", e
                return Response(status=status.HTTP_400_BAD_REQUEST)

        return Response(status=status.HTTP_400_BAD_REQUEST)


""" PLAY CONTENT """
class PlayContent(generics.ListCreateAPIView):
    """<b>Play Ciphered Content</b>"""
    queryset = Content.objects.all()
    serializer_class = ContentSerializer
    allowed_methods = ['get']

    def get(self, request, pk=None, ct=None, pg=None):
        """
        Gets ciphered content by given user id and content id and page of content




        <b>Details</b>

        METHODS : GET



        <b>RETURNS:</b>

        - 200 OK.

        - 400 BAD REQUEST

        ---
        omit_parameters:
        - form
        """
        try:
            int_user_id = int(pk)
            int_content_id = int(ct)
            int_page = int(pg)

            user = User.objects.get(userID=int_user_id)
            # print "user: ", user
            content = Content.objects.get(contentID=int_content_id)
            # print "content: ", content
            purchases = Purchase.objects.all().filter(user=user, content=content)
            # print "purchases: ", purchases

            if len(purchases) > 0:
                if content.pages > 0 and int_page > 0 and int_page <= content.pages:
                    try:
                        crypto = CryptoModule()

                        # create folder tmp if not exists
                        if not os.path.exists("/tmp"):
                            p = subprocess.Popen(["mkdir", "-p","/tmp"])
                            p.wait()

                        player = Player.objects.get(user=user)
                        device = Device.objects.get(player=player)
                        fileKey = genFileKey(user, player, device)
                        # fpath = settings.MEDIA_ROOT+'/'+content.filepath+'/'+content.fileName+pg+".jpg"
                        fpath = "/tmp/storage-mount/"+content.filepath+'/'+content.fileName+pg+".jpg"
                        # print fpath
                        f1 = open(fpath, 'rb')
                        fcifra = crypto.cipherAES(fileKey[0], fileKey[1], f1.read())
                        f1.close()
                        # save to disk
                        # cipheredFileName = settings.MEDIA_ROOT+"/storage/ghosts/ciphered_"+content.fileName+pg
                        cipheredFileName = "/tmp/ciphered_"+content.fileName+pg

                        f2 = open(cipheredFileName, 'wb')
                        deviceKeyPub = crypto.decipherAES(device.deviceHash[0:16], device.deviceHash[32:48], device.deviceKey)
                        deviceKeyPubObj = crypto.rsaImport(deviceKeyPub)

                        # cipher magicKey with device key PUBLIC
                        magicSafe = crypto.rsaCipher(deviceKeyPubObj, user.magicKey)
                        fcifraSafe = str(fcifra).encode('base64')

                        # cardinal don't belong to base64, to do split by #
                        f2.write("#"+magicSafe+"#"+fcifraSafe)
                        f2.close()

                    except Exception as e:
                        print "Error while encrypting!", e
                        return Response(status=status.HTTP_400_BAD_REQUEST)

                    return Response(status=status.HTTP_200_OK, data={'path': cipheredFileName})

            return Response(status=status.HTTP_400_BAD_REQUEST)
        except:
            return Response(status=status.HTTP_400_BAD_REQUEST)


def genFileKey(user=None, player=None, device=None):
    if user==None or player==None or device==None:
        print " TRUE: user==None or player==None or device==None"
        return None

    crypto = CryptoModule()

    userkey = user.userKey
    playerIm = getPlayerKey(user, player)
    playerKeyPub = crypto.publicRsa(playerIm)

    deviceKeyPub = crypto.decipherAES(device.deviceHash[0:16], device.deviceHash[32:48], device.deviceKey)

    # magic used to -> Calculate auxiliar key with userKey and magic value
    magic = CryptoModule.hashingSHA256(datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M'))
    # Save ciphered magicKey on database
    magicKey = crypto.cipherAES(magic[0:16], magic[32:48], magic)
    user.magicKey = magicKey
    # user.save() -> post modifications to DB
    user.save()

    aux = getAuxKey(userkey, magicKey)
    pk = CryptoModule.hashingSHA256(str(playerKeyPub))
    dk = CryptoModule.hashingSHA256(str(deviceKeyPub))

    xor1 = ""
    for i in range(0, len(pk)):
        xor1 += str(logical_function(aux[i], pk[i]))
    hash_xor1 = CryptoModule.hashingSHA256(xor1)

    fileKey = ""
    for i in range(0, len(dk)):
        fileKey += logical_function(hash_xor1[i], dk[i])
    fileKey = CryptoModule.hashingSHA256(fileKey)

    p1 = fileKey[8:24]
    p2 = fileKey[37:53]
    return (p1,p2)


def getAuxKey(userKey, magic):
    if userKey is None or magic is None:
        print "TRUE userKey is None or magic is None"
        return None

    tmp = str(userKey)+str(magic)
    auxKey = CryptoModule.hashingSHA256(tmp)
    return auxKey


def verifyMagic(magicCiphered,user=None, player=None):

    crypto = CryptoModule()

    magicKey = user.magicKey

    playerKey = getPlayerKey(user, player)
    magicPlain = crypto.rsaDecipher(playerKey, magicCiphered)

    # challenge correct
    if magicKey == magicPlain:
        return getAuxKey(user.userKey, magicKey)
    # challenge not accepted
    else:
        return None


def getPlayerKey(user=None, player=None):
    crypto = CryptoModule()

    playerKey = player.playerKey
    pkhash = user.email[:len(user.email)/2]+user.password[len(user.password)/2:]+user.username

    playerHash = crypto.hashingSHA256(str(pkhash))
    return crypto.rsaImport(playerKey, playerHash)


def logical_function(str1, str2):
    return str1 + str2
""" END OF PLAY CONTENT """


class ChallengeKey(generics.ListCreateAPIView):
    """<b>Get the auxiliar key to produce FileKey</b>"""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    allowed_methods = ['post']

    def post(self, request):
        """
        Gets the auxiliar token for produce the FileKey




        <b>Details</b>

        METHODS : POST


        <b>Example:</b>


        {

            "userId": "12",

            "magicKey": "5i9fh938hf83h893hg9384hg9348hg"

        }


        <b>RETURNS:</b>

        - 200 OK.

        - 400 BAD REQUEST

        ---
        omit_parameters:
        - form
        """
        # print request.META['CSRF_COOKIE']
        try:
            if 'userId' in request.data and 'magicKey' in request.data:
                int_id = int(request.data['userId'])
                user = User.objects.get(userID=int_id)
                player = Player.objects.get(user=user)
                magicKeyCiphered = request.data['magicKey']

                auxKey = verifyMagic(magicKeyCiphered, user, player)

                if auxKey is not None:
                    return Response(status=status.HTTP_200_OK, data={'challenge': auxKey})
        except:
            print "Error in request!"
        return Response(status=status.HTTP_400_BAD_REQUEST)


class GET_userIV(generics.ListCreateAPIView):
    """<b>Gets the IV for user</b>"""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    allowed_methods = ['get']

    def get(self, request, un=None):
        """
        Gets the user IV for given username




        <b>Details</b>

        METHODS : GET



        <b>RETURNS:</b>

        - 200 OK.

        - 400 BAD REQUEST

        ---
        omit_parameters:
        - form
        """
        try:
            user = User.objects.get(username=un)
            iv = user.userIV

            return Response(status=status.HTTP_200_OK, data={'iv': iv})
        except:
            pass
        return Response(status=status.HTTP_400_BAD_REQUEST)


class GET_playerIV(generics.ListCreateAPIView):
    """<b>Gets the IV for player</b>"""
    queryset = Player.objects.all()
    serializer_class = PlayerSerializer
    allowed_methods = ['get']

    def get(self, request, un=None):
        """
        Gets the player IV for given username




        <b>Details</b>

        METHODS : GET



        <b>RETURNS:</b>

        - 200 OK.

        - 400 BAD REQUEST

        ---
        omit_parameters:
        - form
        """
        try:
            user = User.objects.get(username=un)
            player = Player.objects.get(user=user)
            iv = player.playerIV

            return Response(status=status.HTTP_200_OK, data={'iv': iv})
        except:
            pass
        return Response(status=status.HTTP_400_BAD_REQUEST)


class SignValidation(generics.ListCreateAPIView):
    """<b>Validate the CC sign</b>"""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    allowed_methods = ['post']

    def post(self, request):
        """
        Validates the sign of a CC




        <b>Details</b>

        METHODS : POST


        <b>Example:</b>


        {

            "username": "daniel",

            "sign": "5i9fh938hf83h893hg9384hg9348hg"

        }


        <b>RETURNS:</b>

        - 200 OK

        - 401 UNAUTHORIZED

        ---
        omit_parameters:
        - form
        """
        # print request.META['CSRF_COOKIE']
        try:
            if 'username' in request.data and 'sign' in request.data:
                username = request.data['username']
                user = User.objects.get(username=username)
                user.userCC
                sign = request.data['sign']
                crypto = CryptoModule()
                pteid = SmartCard()

                ccPubKey = crypto.rsaImport(user.userCCKey)
                data = user.userCC+user.userCC+"abcd"
                check = pteid.veriSign(sign, data, ccPubKey)

                if not check:
                    return Response(status=status.HTTP_200_OK)
                else:
                    return Response(status=status.HTTP_401_UNAUTHORIZED)
        except:
            pass
        return Response(status=status.HTTP_401_UNAUTHORIZED)


class ContentPages(generics.ListCreateAPIView):
    """<b>Content pages number</b>"""
    queryset = Content.objects.all()
    serializer_class = ContentSerializer
    allowed_methods = ['get']

    def get(self, request, pk=None):
        """
        Gets number of pages of given content id




        <b>Details</b>

        METHODS : GET



        <b>RETURNS:</b>

        - 200 OK.

        - 400 BAD REQUEST

        ---
        omit_parameters:
        - form
        """
        try:
            int_id = int(pk)
            content = Content.objects.get(contentID=int_id)
            pages = str(content.pages)

            return Response(status=status.HTTP_200_OK, data={'pages': pages})
        except:
            pass
        return Response(status=status.HTTP_400_BAD_REQUEST)
