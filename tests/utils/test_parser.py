from ops.utils import config_handler, constants
import io
import logging
from jproperties import Properties

logger = logging.getLogger(__name__)


class TestParser:
    def test_yaml_remove_extra_keys(self):
        current_str = """# commit
        key1: value1
        key2: value2
        extra_key: value_extra  # 这个键值对在 full_config.yaml 中不存在
        nested:
            key3: value3
            extra_nested_key: value_extra_nested  # 这个键值对在 full_config.yaml 中不存在
        list_key:
            - item1
            - item2
            - extra_item  # 这个项在 full_config.yaml 中不存在
        """
        full_str = """
        key1: value1
        key2: value2
        nested:
            key3: value3
        list_key:
            - item1
            - item2            
        """
        format1, current, yaml = config_handler.parse_content(current_str)
        format2, full, yaml = config_handler.parse_content(full_str)
        config_handler.yaml_cpx(full, current)
        logging.info("\n%s", config_handler.yaml_to_string(current, yaml))

    def test_yaml_patch(self):
        current_str = """# commit
        key1: value1
        key2: value2
        extra_key: value_extra
        nested:
            key3: value3
            extra_nested_key: value_extra_nested
        list_key:
            - item1
            - item2
            - extra_item
        """
        patch_str = """
        key1: value1_new
        list_key:
            - item1
            - item2            
        """
        format1, current, yaml = config_handler.parse_content(current_str)
        format2, patch, yaml = config_handler.parse_content(patch_str)
        config_handler.yaml_patch(patch, current)
        logging.info("\n%s", config_handler.yaml_to_string(current, yaml))

    def test_parse_content(self):
        cstr = """# comment
vod.system.type=MFC

media_search_index.media_search_index={   "properties" : {                              "certifications" : {             "type" : "nested",             "dynamic" : "false",             "properties" : {               "certificate" : {                 "type" : "keyword"               },               "country" : {                 "type" : "keyword"               },               "countryCode" : {                 "type" : "keyword"               }             }           },           "clouds" : {             "type" : "integer"           },           "cloudsAudioLanguage" : {             "type" : "keyword"           },           "companies" : {             "type" : "keyword"           },           "disCompanies" : {             "type" : "keyword"           },           "connectedTime" : {             "type" : "long"           },           "countries" : {             "type" : "long"           },           "recommendValue" : {             "type" : "double"           },           "like" : {             "type" : "long"           },            "unlike" : {             "type" : "long"           },           "viewedAll" : {             "type" : "long"           },           "viewedDay" : {             "type" : "long"           },           "viewedWeek" : {             "type" : "long"           },           "viewedMonth" : {             "type" : "long"           },           "viewedYear" : {             "type" : "long"           },          "createTime" : {             "type" : "date",             "format" : "yyyy-MM-dd HH:mm:ss||yyyy-MM-dd||epoch_millis"           },                              "firstLanguage" : {             "type" : "keyword"           },           "genres" : {             "type" : "long"           },                   "id" : {             "type" : "long"           },                              "lastAirDateInt" : {             "type" : "integer"           },                   "seriesId" : {             "type" : "long"           },                      "seasonId" : {             "type" : "long"           },           "season" : {             "type" : "integer"           },                      "episode" : {             "type" : "integer"           },                      "linkedLastAirDateInt" : {             "type" : "integer"           },            "mediaType" : {             "type" : "integer"           },           "metaId" : {             "type" : "keyword"           },                  "originalTitle" : {             "type" : "keyword",             "index" : false,             "doc_values" : false           },           "playlists" : {             "type" : "nested",             "properties" : {               "playlistId" : {                 "type" : "long"               },               "showSeq" : {                 "type" : "long"               }             }           },           "popularity" : {             "type" : "double"           },           "ppId" : {             "type" : "keyword"           },           "rating" : {             "type" : "double"           },           "weightRating" : {             "type" : "double"           },           "releaseDateInt" : {             "type" : "integer"           },                    "status" : {             "type" : "integer"           },                     "tags" : {             "type" : "nested",             "properties" : {               "score" : {                 "type" : "double"               },               "tagId" : {                 "type" : "keyword"               }             }           },           "year" : {             "type" : "integer"           },           "mediaSeq" : {             "type" : "integer"           },           "tagIds" : {             "type" : "keyword"           }, 		  "publishLastModifyTime" : {             "type" : "long"           },           "lastConnectedTime" : {             "type" : "long"           },           "runtime" : {             "type" : "long"           }                    } }


##################################
# 0: crypt disable
# 1: crypt enable

#
mfc.api.crypt=1
mfc.api.crypt.debug.time=1
#mfc.api.crypt.{api_name}=0/1 0 is disable 1:enable

mfc.api.arg.jaq.key=8ff9f0db-6f7b-4492-98c1-8226f81956eb

weightRatingId=4,9,508,10011,10021,9407,9426
backgroudImageToBackdropVer=:10202,2009999;mfc-kids:10202,3019999
playlistMediaTypeDesc=3,7,8:Movie;4,6,9,10:TV Shows;-1:

mfc.meta.play.enter.detail.check.list=trailers
mfc.meta.play.enter.detail.check.map=tmdbId-1
mfc.meta.hot.detailViewMode=1

mfc_vms_app_var1=VVam4P8eUzTPNqbk2oJSC_Hu9HJwSI3GMY4dO7m_CTYjlnxt3_ytmEZCosO9W7qHBr4bLWd9G_5Vkge1jepT1eCX08H259W6jm0u-J-m8zOaGS9Vjezp6JKBUZUU4prmsG7q-SmKxi_VTVVkJMjHAqshJVIXCNsdlv-DYfubpZCg1WCedVnd2D2IsS4bX7C2c0F-qGT6S_lvjnrJKoT-LPTsOp1rI6LxBirk3HQdVqzr0agyqWkNARawdYt9jbqDrtfjrGZVXRY1I5WUhc465yt3NvF-W5X45vtQ3Ox7gqkENvHKHuLjCQupzScyWFikT1fpEgIUued5sH6SZ3Z5kFc7Hi748Sk2-TkYYLYm0eDFv3_RPVGJhp56qI8A7xDZWoRgYY3EKDGiyuDVS_x-MHpBb6XF1jszZYzJwYBNgwxJr9VpGqliWAt6voy0HxL6nQ1Lc-cw24qK1jfedWcRiyN3Xc5S0-Q_g7M1iKfjOuqKqwNhw3ehuV0GGQXspPkM3Ejt8xSi9m2TbVqXgk2QZ47vmio0N7wUsN8EygExpESYKKkHYpzWnQbrEPNgf7HxIAdWas8i4yzEKRyjINHopUDDlPPci9BS1dZoKH6Xyfs
mfc_vms_app_var2=Gehqa8HMDxDBNYoqm3ZU2g
mfc_vms_as_var1=aYpEVM_pi-BaT7KEt6MzZtysJSPuT4hCUhtAaQIOg9Wd5LrF-lRuSQpNMbskrZsXd9jYLl9rmhrzCaM30foWE7lgdqTQGN8khJczCYDAZ5rF9u1rTvL-tWrELU6zQrDLvEtI9eDwYzDWkiVvfAwvTfPI6TMMh5YgqAsyQWSfA2w

mfc_vms_as_var2=864000
mfc_vms_as_var3=Gehqa8HMDxDBNYoqm3ZU2g

#Formats example:
#{id} = {name}
#{id}:{name}
#{id}={name}

-100=WEB
1=TEST
9000100=WEB

1000100=BTV
1000200=MFC
1000300=TVE
1000301=BTVE
2000100=AKWD
2000200=WXSD
3000100=HQBZ
3000200=RIO100
3000300=PDL
3000400=SWL
3000500=CELLSHOP/REDPLAY
3000600=LEANDRO
3000700=PDLDUOSAT
3000800=STARTTV
3000900=XTV

# mfc.vms.api.auto.reactivate=0
# mfc.user.auto.add=0

mfc.trial.vendors=100
mfc.not.pre.installed.auto.create.user=true

# secondAudio关闭ignite查询,0-否，1-是
mfc.ignite.secondAudio.close=0
# 加载secondAudio到ignite,0-否，1-是
mfc.ignite.secondAudio.loadcache=1

#mfc.ignite.secondAudio.loadcache=2

banner.cache.expire=1

mfc.trial.user.play.banTime.isCrossDay=false
mfc.user.info.cache.enable=true
mfc.free.user.play.service.limitation.enable=false
mfc.redis.cache.expire.time=1800L
mfc.user.biz.cache.expire.time=1800L
mfc.trial.user.play.banStartTime=10:50
mfc.trial.user.play.banEndTime=11:00


kids.oauth.login.freeDays=9999
kids.oauth.login.trail=0
kids.oauth.login.enableFree=1
kids.oauth.login.disableExpireDate=1

mfc-pnguava-max-size-userVendorCache=200000
mfc-pnguava-exp-userVendorCache=600
mfc-pnguava-enable-userCloudCache=false
mfc-pnguava-max-size-userCloudCache=200000
mfc-pnguava-exp-userCloudCache=300
mfc-pnguava-max-size-searchTypeCache=200000
mfc-pnguava-exp-searchTypeCache=600
mfc-pnguava-max-size-regionHasTheaterMovieCache=200000
mfc-pnguava-exp-regionHasTheaterMovieCache=600
mfc-pnguava-max-size-personPhotoCache=200000
mfc-pnguava-exp-personPhotoCache=600
mfc-pnguava-max-size-mediaDetailIdCache=200000
mfc-pnguava-exp-mediaDetailIdCache=600
mfc-pnguava-max-size-mediaAwardIdLangCache=600
mfc-pnguava-exp-mediaAwardIdLangCache=200000
mfc-pnguava-max-size-mediaCloudCache= 100000
mfc-pnguava-exp-mediaCloudCache= 300
mfc-pnguava-max-size-mediaAllDetailCache=100000
mfc-pnguava-exp-mediaAllDetailCache=300
mfc-pnguava-max-size-artworkCache=100000
mfc-pnguava-exp-artworkCache=3600
mfc-es-pagesize-mediacloud-videoid=10000
mfc-pnguava-exp-mediaDetailSearchCache=300
mfc-pnguava-max-size-mediaDetailSearchCache=50000
mfc-pnguava-exp-videoIdCache=600
mfc-pnguava-log-enabled=false
webapi.cache.control.api-playlist-videos-v1=1800
webapi.cache.control.api-person-detail-v1=1800
webapi.cache.control.api-media-detail-v1=1800
mfc-pnguava-exp-personCache=300
mfc-pnguava-max-size-personCache=10000
mfc-pnguava-exp-personSetCache=300
mfc-pnguava-max-size-personSetCache=10000

#Sun Jul 23 09:27:25 CST 2017
fb97e771-cb31-4aa1-a0be-37a84f4c8396=+F8TDyik5VlAc90/hy58nA70mK06yJRiuSGJ64/zufDoUknB3nfseA\=\=
#Wed Sep 20 14:15:35 CST 2017
8ff9f0db-6f7b-4492-98c1-8226f81956eb=mI/HDqIkPa+u2APKeD7VT/OxUjoljtp5jcHv9LSA21z8p7eYCagU/A\=\=

ijiamiLib.path=ijiamiLib

vod.meta.play.count.optimize.enabled=true
mfc.search.target=withPerson=true&filter=mediaType:3,4,7,8&searchAll=true&timeLimit=false
mfc.search.kids.target=kidsWithPerson=false&filter=genre:12,5,14,18,19:ne;genre:3;certifications.countryCode:us;certifications.certificate:G,TV-G,TV-Y,TV-Y7,TV-Y7-FV,PG,TV-PG;&timeLimit=false

meta.cache.expireMinutes=5
mfc.meta.listCache.expireSeconds=3000
mfc.meta.runtime.unit=1
like.enable=false
mfc.account.info.redis.cache.expire.time=600

system.app.id.box=stb
system.app.id.mobile=mobile
system.app.id.hot.box=hot
system.app.id.hot.mobile=hot-mobile

cloud-pkg.cache=220313170018000001;220313170018000001_220313170028000001;220313170018000001_220313170032000001

vod.api.crypt.enable=true
vod.api.token.enable=true
        """
        format, current, yaml = config_handler.parse_content(cstr)
        current["nested.key3"] = "value3_new"
        current["key1"] = 3333
        logger.info(current["nested.key3"])
        logger.info("\n%s", config_handler.properties_to_string(current))

    def test_properties_remove_extra_keys(self):
        current_str = """#comment
        key1=value1
        extra_key=value_extra
        nested.key3=value3
        # comment2222
        # [section]
        nested.key-1.key-1-1=value_prod
        nested.arr[0].key1=aaa1
        nested.arr[0].key2=aaa2
        nested.arr[1].key1=bbb_prod1
        nested.arr[1].key2=bbb_prod2
        """
        full_str = """#comment
        key1=value1
        nested.key3=value3
        # comment2222
        # [section]
        nested.key-1.key-1-1=value_test
        nested.arr[1].key1=bbb_test1
        nested.arr[1].key2=bbb_test2
        """
        f1, current, yml1 = config_handler.parse_content(current_str)
        f2, full, yml2 = config_handler.parse_content(full_str)
        config_handler.properties_cpx(full, current)
        logger.info("\n%s", config_handler.properties_to_string(current))

    def test_properties_patch(self):
        current_str = """#comment
        key1=value1
        extra_key=value_extra
        nested.key3=value3
        # comment2222
        [section]
        nested.key-1.key-1-1=value_prod
        nested.arr[0].key1=aaa1
        nested.arr[0].key2=aaa2
        nested.arr[1].key1=bbb_prod1
        nested.arr[1].key2=bbb_prod2
        """
        patch_str = """#comment
        key1=value1_new
        nested.key3=value3_new
        [section]
        nested.key-1.key-1-1=value_new
        """
        f1, current, yml1 = config_handler.parse_content(current_str)
        f2, patch, yml2 = config_handler.parse_content(patch_str)
        config_handler.properties_patch(patch, current)
        logger.info("\n%s", config_handler.properties_to_string(current))

    def test_jproperties(self):
        current_str = """#comment
        key1=value1
        extra_key=value_extra
        nested.key3=value3
        # comment2222
        nested.key-1.key-1-1=value_prod
        nested.arr[0].key1=aaa1
        nested.arr[0].key2=aaa2
        nested.arr[1].key1=bbb_prod1
        nested.arr[1].key2=bbb_prod2
        """
        p = Properties()
        p.load(current_str, encoding="utf-8")
        output_stream = io.BytesIO()
        p.store(out_stream=output_stream, encoding="utf-8")
        t = output_stream.getvalue()
        logger.info("\n%s", t)
