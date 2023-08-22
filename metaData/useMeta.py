# -*- coding: utf-8 -*-

from pandas import DataFrame
import os, pickle


useMeta = """BDTYP_CD,코드값의미,주거여부,IDF_type
01000,단독주택,1,house
01001,단독주택,1,house
01002,다중주택,1,apt
01003,다가구주택,1,apt
01004,공관,1,house
02000,공동주택,1,apt
02001,아파트,1,apt
02002,연립주택,1,apt
02003,다세대주택,1,apt
02004,생활편익시설,0,retail
02005,부대시설,0,carpark
02006,복리시설,0,lecturehall
02007,기숙사,0,apt
03000,제1종근린생활시설,0,retail
03001,소매점,0,retail
03002,휴게음식점,0,rest
03003,이(미)용원,0,retail
03004,일반목욕장,0,amusement
03005,의원,0,med
03006,체육장,0,sportscenter
03007,마을공동시설,0,lecturehall
03011,대피소,0,lecturehall
03012,공중화장실,0,toilet
03013,세탁소,0,retail
03014,치과의원,0,med
03015,한의원,0,med
03016,침술원,0,med
03017,접골원,0,med
03018,조산소,0,med
03019,탁구장,0,sportscenter
03020,체육도장,0,sportscenter
03021,마을공회당,0,lecturehall
03022,마을공동작업소,0,lecturehall
03023,마을공동구판장,0,retail
03024,개방공중화장실,0,toilet
03100,공공시설,0,pub
03101,동사무소,0,pub
03102,경찰서,0,pub
03103,파출소,0,pub
03104,소방서,0,pub
03105,우체국,0,pub
03106,전신전화국,0,pub
03107,방송국,0,off
03108,보건소,0,med
03109,공공도서관,0,pub
03110,지역의료보험조합,0,pub
03199,기타공공시설,0,pub
03999,기타제1종근생,0,retail
04000,제2종근린생활시설,0,retail
04001,일반음식점,0,rest
04002,휴게음식점,0,rest
04003,기원,0,amusement
04004,서점,0,retail
04005,제조업소,0,factory
04006,수리점,0,off
04007,게임제공업소,0,amusement
04008,사진관,0,retail
04009,표구점,0,retail
04010,학원,0,lecturehall
04011,장의사,0,off
04012,동물병원,0,med
04014,독서실,0,lecturehall
04015,총포판매소,0,retail
04016,단란주점,0,amusement
04017,의약품도매점,0,retail
04018,자동차영업소,0,retail
04019,안마시술소,0,amusement
04020,노래연습장,0,amusement
04021,세탁소,0,retail
04022,멀티미디어문화컨텐츠설비제공업소,0,amusement
04023,복합유통.제공업소,0,amusement
04101,테니스장,0,outdoor
04102,체력단련장,0,gym
04103,에어로빅장,0,sportscenter
04104,볼링장,0,sportscenter
04105,당구장,0,amusement
04106,실내낚시터,0,amusement
04107,골프연습장,0,sportscenter
04199,기타운동시설,0,gym
04201,교회,0,lecturehall
04202,성당,0,lecturehall
04203,사찰,0,lecturehall
04299,기타종교집회장,0,lecturehall
04301,극장(영화관),0,concerthall
04302,음악당,0,concerthall
04303,연예장,0,concerthall
04304,비디오물감상실,0,concerthall
04305,비디오물소극장,0,concerthall
04399,기타공연장,0,concerthall
04401,금융업소,0,off
04402,사무소,0,off
04403,부동산중개업소,0,off
04404,결혼상담소,0,off
04405,출판사,0,off
04499,기타사무소,0,off
04999,기타제2종근생,0,retail
04505,고시원,0,apt
05000,문화 및 집회시설,0,lecturehall
05101,교회,0,lecturehall
05102,성당,0,lecturehall
05103,사찰,0,lecturehall
05104,기도원,0,lecturehall
05105,수도원,0,lecturehall
05106,수녀원,0,lecturehall
05107,제실,0,lecturehall
05108,사당,0,lecturehall
05109,납골당,0,lecturehall
05199,기타종교집회장,0,lecturehall
05201,극장(영화관),0,concerthall
05202,음악당,0,concerthall
05203,연예장,0,concerthall
05204,서어커스장,0,concerthall
05205,비디오물감상실,0,concerthall
05206,비디오물소극장,0,concerthall
05299,기타공연장,0,concerthall
05301,예식장,0,lecturehall
05302,회의장,0,lecturehall
05303,공회당,0,lecturehall
05304,마권장외발매소,0,off
05305,마권전화투표소,0,off
05399,기타집회장,0,lecturehall
05401,경마장,0,amusement
05402,자동차경기장,0,amusement
05403,체육관,0,sportscenter
05404,운동장,0,outdoor
05499,기타관람장,0,museum
05501,박물관,0,museum
05502,미술관,0,museum
05503,과학관,0,museum
05504,기념관,0,museum
05505,산업전시장,0,museum
05506,박람회장,0,museum
05599,기타전시장,0,museum
05601,동물원,0,museum
05602,식물원,0,museum
05603,수족관,0,museum
05699,기타동_식물원,0,museum
05999,기타문화및집회시설,0,lecturehall
06000,판매 및 영업시설,0,retail
06100,도매시장,0,retail
06201,시장,0,retail
06202,백화점,0,retail
06203,대형판매점,0,retail
06204,대형점,0,retail
06205,대규모소매점,0,retail
06299,기타소매시장,0,retail
06301,상점,0,retail
06302,게임제공업소,0,amusement
06303,여객자동차터미널,0,terminal
06304,화물터미널,0,carpark
06305,철도역사,0,terminal
06306,공항시설,0,terminal
06307,항만시설(터미널),0,carpark
06308,종합여객시설,0,terminal
06309,멀티미디어문화콘텐츠설비제공업소,0,amusement
06310,복합유통_제공업소,0,amusement
06999,기타판매및영업시설,0,retail
07000,의료시설,0,med
07101,종합병원,0,med
07102,산부인과병원,0,med
07103,치과병원,0,med
07104,한방병원,0,med
07105,정신병원,0,med
07106,격리병원,0,med
07107,병원,0,med
07108,요양소,0,med
07199,기타병원,0,med
07201,장례식장,0,lecturehall
07301,전염병원,0,med
07302,마약진료소,0,med
07999,기타의료시설,0,med
08000,교육연구 및 복지시설,0,lab
08001,교육(연수)원,0,univ
08002,직업훈련소,0,univ
08003,학원,0,lecturehall
08004,연구소,0,lab
08005,도서관,0,pub
08101,초등학교,0,sch
08102,중학교,0,sch
08103,고등학교,0,sch
08104,대학교,0,univ
08105,전문대학,0,univ
08106,대학,0,univ
08199,기타학교,0,sch
08201,유치원,0,sch
08202,영유아보육시설,0,pub
08203,어린이집,0,pub
08204,아동복지시설,0,pub
08299,기타아동관련시설,0,pub
08300,노인복지시설,0,pub
08400,사회복지시설,0,pub
08500,근로복지시설,0,pub
08601,청소년수련원(관),0,lecturehall
08602,유스호스텔,0,acc
08603,청소년문화의집,0,lecturehall
08699,기타생활권수련시설,0,lecturehall
08700,야영장 시설,0,warehouse
08701,청소년수련원(관),0,lecturehall
08702,청소년야영장,0,warehouse
08799,기타자연권수련시설,0,lecturehall
08800,노유자시설,0,pub
08999,기타교육연구및복지시설,0,lab
09000,운동시설,0,gym
09001,체육관,0,sportscenter
09002,운동장시설,0,outdoor
09003,탁구장,0,sportscenter
09004,체육도장,0,sportscenter
09005,테니스장,0,outdoor
09006,체력단련장,0,gym
09007,에어로빅장,0,sportscenter
09008,볼링장,0,sportscenter
09009,당구장,0,amusement
09010,실내낚시터,0,amusement
09011,골프연습장,0,sportscenter
09999,기타운동시설,0,gym
10000,업무시설,0,off
10101,국가기관청사,0,pub
10102,자치단체청사,0,pub
10103,외국공관,0,pub
10199,기타공공업무시설,0,pub
10201,금융업소,0,off
10202,오피스텔,0,apt
10203,신문사,0,off
10204,사무소,0,off
10299,기타일반업무시설,0,off
11000,숙박시설,0,acc
11101,호텔,0,acc
11102,여관,0,acc
11103,여인숙,0,acc
11199,기타일반숙박시설,0,acc
11201,관광호텔,0,acc
11202,수상관광호텔,0,acc
11203,한국전통호텔,0,acc
11204,가족호텔,0,acc
11205,휴양콘도미니엄,0,acc
11299,기타관광숙박시설,0,acc
12000,위락시설,0,amusement
12001,단란주점,0,amusement
12002,유흥주점,0,amusement
12003,특수목욕장,0,amusement
12004,유기장,0,amusement
12005,투전기업소,0,amusement
12006,무도장(학원),0,amusement
12007,주점영업,0,amusement
12008,카지노업소,0,amusement
12009,유원시설업의 시설,0,amusement
12999,기타위락시설,0,amusement
13000,공장,0,factory
13100,일반공장,0,factory
13200,공해공장,0,factory
14000,창고시설,0,warehouse
14001,창고,0,warehouse
14002,하역장,0,warehouse
14999,기타창고시설,0,warehouse
15000,위험물저장처리시설,0,factory
15001,주유소,0,warehouse
15002,액화석유가스충전소,0,warehouse
15005,액화가스취급소,0,warehouse
15006,액화가스판매소,0,warehouse
15009,석유판매소,0,warehouse
16000,자동차관련시설,0,carpark
16001,주차장,0,carpark
16002,세차장,0,warehouse
16003,폐차장,0,factory
16004,검사장,0,factory
16005,매매장,0,carpark
16006,정비공장,0,factory
16007,운전학원,0,lecturehall
16008,정비학원,0,lecturehall
16009,차고,0,carpark
16010,주기장,0,warehouse
16999,기타자동차관련시설,0,carpark
17000,동식물관련시설,0,warehouse
17003,도축장,0,warehouse
17004,도계장,0,warehouse
17005,버섯재배사,0,warehouse
17006,종묘배양시설,0,warehouse
17007,온실,0,warehouse
17101,축사,0,warehouse
17102,양잠,0,warehouse
17103,양봉,0,warehouse
17104,양어시설,0,warehouse
17105,부화장,0,warehouse
17201,가축용운동시설,0,outdoor
17202,인공수정센터,0,warehouse
17203,관리사,0,warehouse
17204,가축용창고,0,warehouse
17205,가축시장,0,warehouse
17206,동물검역소,0,warehouse
17207,실험동물사육시설,0,warehouse
17299,기타가축시설,0,warehouse
17999,기타동식물관련시설,0,warehouse
18000,분뇨_쓰레기처리시설,0,factory
18001,분뇨처리시설,0,factory
18002,폐기물처리시설,0,factory
18003,폐기물재활용시설,0,factory
18004,고물상,0,factory
18999,기타분뇨쓰레기처리시설,0,factory
19000,공공용시설,0,pub
19002,감화원,0,prison
19005,방송국,0,off
19006,전신전화국,0,pub
19007,촬영소,0,off
19103,소년분류심사원,0,off
20000,묘지관련시설,0,lecturehall
20001,화장장,0,lecturehall
20002,납골당,0,lecturehall
20003,묘지에 부수되는 건축물,0,warehouse
20999,기타묘지관련시설,0,warehouse
21000,관광휴게시설,0,amusement
21001,야외음악당,0,outdoor
21002,야외극장,0,outdoor
21003,어린이회관,0,lecturehall
21004,관망탑,0,museum
21005,휴게소,0,retail
21006,관광지시설,0,amusement
21999,기타관광휴게시설,0,amusement
27000,발전시설,0,serverroom
27999,기타발전시설,0,serverroom
90000,거리가게,0,retail
90001,가로판매대,0,retail
90002,구두수선대,0,retail""".split('\n')

def gen_useMeta():
    n_item = len(useMeta) - 1
    header = useMeta[0].split(',')
    items = ['a']*n_item
    for idx, item in enumerate(useMeta[1:]):
        items[idx] = item.split(',')
    df = DataFrame(items, columns = header)
    savePath = os.path.join(os.getcwd(), 'Meta')
    if os.path.isdir(savePath) == False:
        os.mkdir(savePath)
    filePath = os.path.join(savePath, 'useMeta.pkl')
    with open(filePath, 'wb') as f:
        pickle.dump(df, f)
    return df        

def load_useMeta():
    
    df = gen_useMeta()

    return df            
       
        
#%%
if __name__ == '__main__':
    dd = gen_useMeta()