function getUrl(signatureCipher) {
    let url = new URL("http://example.com/path/index.html?" + signatureCipher)
    let s = decodeURIComponent(url.searchParams.get('s'));
    let furl = decodeURIComponent(url.searchParams.get('url'));

    var ML = {
        KT: function(a) {
            a.reverse();
        },
        Gc: function(a, b) {
            var c = a[0];
            a[0] = a[b % a.length];
            a[b % a.length] = c;
        },
        n1: function(a, b) {
            a.splice(0, b);
        }
    };
    
    nCa = function(a) {
        a = a.split("");
        ML.Gc(a, 21);
        ML.KT(a, 67);
        ML.n1(a, 2);
        ML.Gc(a, 27);
        ML.n1(a, 1);
        ML.KT(a, 75);
        ML.Gc(a, 46);
        ML.n1(a, 2);
        return a.join("");
    };

    furl += "&sig=" + nCa(s);
    return furl;
}

console.log(getUrl("s=9JAJfQdSswRQIhAIKieF3Ve9jKPdWJgJfjYOlW0dPyuO8SAZj2bwzV13IZAiA_eqdlvKc8mDDRul9SI%3Dt6VOzz3U5ncvdiXJ6ZtUidVw%3D%3Dg%3Dg\u0026sp=sig\u0026url=https://rr4---sn-uxax3vh50nugp5-8pxy.googlevideo.com/videoplayback%3Fexpire%3D1728524003%26ei%3Dg9oGZ6ngCZehi9oPtIfHkAc%26ip%3D194.96.52.33%26id%3Do-AGD0k2JyrdI7mGqkbq9-4oTRSO2fdrhGxPR_RRdcHgeZ%26itag%3D136%26aitags%3D133%252C134%252C135%252C136%252C160%252C242%252C243%252C244%252C247%252C278%252C597%252C598%26source%3Dyoutube%26requiressl%3Dyes%26xpc%3DEgVo2aDSNQ%253D%253D%26met%3D1728502403%252C%26mh%3DRG%26mm%3D31%252C29%26mn%3Dsn-uxax3vh50nugp5-8pxy%252Csn-c0q7lnz7%26ms%3Dau%252Crdu%26mv%3Dm%26mvi%3D4%26pl%3D21%26rms%3Dau%252Cau%26initcwndbps%3D1028750%26siu%3D1%26bui%3DAXLXGFRXbcJmFmH9tbD7SXqtrEzOfSzCrr5oGkWy27wnXlS-qsZ7jI1iEh7C2Npxu0RpRQoEqA%26spc%3D54MbxWkttv3zqCBQ23OWO85QA43ajxDaUK3GrM_tNj3-9aLAgrOda9JeGy7L-TrrmT4CZitjzA%26vprv%3D1%26svpuc%3D1%26mime%3Dvideo%252Fmp4%26ns%3D3COnTMmQDjKxDgmYyCz56IsQ%26rqh%3D1%26gir%3Dyes%26clen%3D31233986%26dur%3D218.160%26lmt%3D1725674119907605%26mt%3D1728501418%26fvip%3D5%26keepalive%3Dyes%26fexp%3D51300760%26c%3DMWEB%26sefc%3D1%26txp%3D5309224%26n%3Duwf2h1d8ccU7kCqxB%26sparams%3Dexpire%252Cei%252Cip%252Cid%252Caitags%252Csource%252Crequiressl%252Cxpc%252Csiu%252Cbui%252Cspc%252Cvprv%252Csvpuc%252Cmime%252Cns%252Crqh%252Cgir%252Cclen%252Cdur%252Clmt%26lsparams%3Dmet%252Cmh%252Cmm%252Cmn%252Cms%252Cmv%252Cmvi%252Cpl%252Crms%252Cinitcwndbps%26lsig%3DACJ0pHgwRAIgJ3uZv9CJHBhfcloKQbTGUXvZvHCcFKllXSVXLURsNY4CIBjK7Ohb5Tgj1K6IgBWxD9AkGxS2DNk9ETaw0UaGFAzs"))