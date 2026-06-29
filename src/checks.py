"""
Pure helper functions for email verification.
No side effects — all deterministic pure functions or DNS lookups.
"""

import re
import random
import string
import smtplib
import logging
from email.utils import parseaddr
import dns.resolver

logger = logging.getLogger(__name__)

# ── Disposable domains (embedded — no network at runtime) ──────────────────
DISPOSABLE_DOMAINS: set[str] = {
    # Most common disposable providers
    "mailinator.com", "guerrillamail.com", "tempmail.com", "10minutemail.com",
    "yopmail.com", "sharklasers.com", "throwaway.email", "mailnesia.com",
    "maildrop.cc", "temp-mail.org", "trashmail.com", "getairmail.com",
    "emailondeck.com", "dispostable.com", "tempinbox.com", "spamgourmet.com",
    "mailexpire.com", "harakirimail.com", "fakemailgenerator.com",
    "mailmetrash.com", "mintemail.com", "spambox.us", "maileater.com",
    "dodgeit.com", "mytrashmail.com", "trash2000.com", "mailexpire.com",
    "sneakemail.com", "tempalias.com", "jetable.org", "anonym.email",
    "anonymize.com", "boun.cr", "byom.de", "chacuo.net", "cool.fr.nf",
    "correotemporal.org", "courrieltemporaire.com", "demail.com",
    "emailfake.com", "emailtemporario.com.br", "emailtemporanee.com",
    "fakingemail.com", "getnada.com", "guerrillamail.org", "guerrillamail.net",
    "guerrillamail.biz", "hizli.email", "inkomz.com", "ipn.li",
    "koszmail.pl", "mail-temporaire.fr", "mail.by", "mail.mezimages.net",
    "mail.tm", "mail4trash.com", "mailcatch.com", "mailexpire.com",
    "mailin8r.com", "mailinator2.com", "mailinator.net", "mailinator.org",
    "mailinator.us", "mailmetrash.com", "mailsac.com", "mailtemp.net",
    "moburl.com", "mt2009.com", "my10minutemail.com", "nada.email",
    "nowmymail.com", "nurfuerspam.de", "oneoffemail.com", "oopi.org",
    "outlook.at", "pfui.ru", "poofy.org", "privy-mail.com", "proxymail.eu",
    "putthisinyourspamdatabase.com", "quickinbox.com", "rcpt.at",
    "receive-sms-now.com", "receive-sms.cc", "recursor.net",
    "regbypass.com", "schafmail.de", "sialkotcity.com", "sify.com",
    "smtp33.com", "spam.la", "spam.su", "spam4.me", "spamavert.com",
    "spambob.com", "spambob.net", "spambob.org", "spambog.com",
    "spambog.de", "spambog.net", "spambog.ru", "spamcannon.com",
    "spamcannon.net", "spamcero.com", "spamcorptastic.com", "spamcowboy.com",
    "spamcowboy.net", "spamcowboy.org", "spamday.com", "spamex.com",
    "spamfree24.com", "spamfree24.de", "spamfree24.net", "spamfree24.org",
    "spamgourmet.com", "spamgourmet.net", "spamgourmet.org", "spamhereplease.com",
    "spamhole.com", "spamify.com", "spaminator.de", "spamkill.info",
    "spaml.com", "spamlot.net", "spammotel.com", "spamobox.com",
    "spamspy.com", "spamstack.net", "spamthis.co.uk", "spamthisplease.com",
    "spamtrail.com", "spamtroll.net", "spamwc.de", "speed.1s.fr",
    "suremail.info", "teewars.org", "teleworm.us", "temp-emails.com",
    "temp-mail.com", "temp-mail.de", "temp-mail.info", "temp-mail.org",
    "temp-mail.ru", "tempaddress.net", "tempalias.com", "tempe-mail.com",
    "tempemail.biz", "tempemail.co.za", "tempemail.com", "tempemail.net",
    "tempinbox.co.uk", "tempinbox.com", "tempmail.de", "tempmail.eu",
    "tempmail.it", "tempmail.net", "tempmail.org", "tempmail.us",
    "tempmail2.com", "tempmaildemo.com", "tempmailer.com", "tempmailer.de",
    "tempomail.com", "temporaryemail.net", "temporaryemail.us",
    "temporaryforwarding.com", "temporaryinbox.com", "thanksnospam.info",
    "thankyou2010.com", "thc.st", "thecloudbox.com", "thisisnotmyrealemail.com",
    "throwawayemail.com", "tilien.com", "tittbit.in", "toiea.com",
    "topmail.com", "tormail.org", "trash2009.com", "trash-amil.com",
    "trash-me.com", "trash2009.com", "trashcanmail.com", "trashmail.at",
    "trashmail.com", "trashmail.de", "trashmail.me", "trashmail.net",
    "trashmail.org", "trashmailer.com", "trashymail.com", "trashymail.net",
    "tyldd.com", "uggsrock.com", "umail.net", "upliftnow.com", "uplipht.com",
    "venompen.com", "veryrealemail.com", "vidchart.com", "viralemail.com",
    "vpn.st", "vsimcard.com", "vubby.com", "walala.org", "walkmail.net",
    "walkmail.ru", "webemail.me", "webm4il.info", "webmail.uu.gl",
    "wegwerfmail.de", "wegwerfmail.net", "wegwerfmail.org", "wh4f.org",
    "whyspam.me", "willselfdestruct.com", "winemaven.info", "wronghead.com",
    "wuzup.net", "xagloo.com", "xemaps.com", "xents.com", "xmaily.com",
    "xoxy.net", "yep.it", "yogamaven.com", "yopmail.com", "yopmail.fr",
    "yopmail.net", "ypmail.webarnak.fr.eu.org", "yuurok.com", "zehnminutenmail.de",
    "zippymail.info", "zoaxe.com", "zoemail.com", "zoemail.net", "zoemail.org",
    "spambox.org", "trashymail.net", "emailgo.de", "fremail.de",
    "maildu.de", "mox.pp.ua", "nepwk.com", "0815.ru", "0x00.name",
    "0x01.name", "0x02.name", "0x03.name", "0x04.name", "0x05.name",
    "0x06.name", "0x07.name", "0x08.name", "0x09.name", "0x0a.name",
    "0x0b.name", "0x0c.name", "0x0d.name", "0x0e.name", "0x0f.name",
    "10minutemail.net", "10minutemail.org", "10minutemail.info",
    "20minutemail.com", "20minutemail.de", "30minutemail.com",
    "30minutemail.net", "60minutemail.com", "a-bc.net", "actionmail.com",
    "adfever.com", "antispam24.de", "armyspy.com", "avastu.com",
    "awsoo.com", "azazazatashkent.tk", "banit.club", "bareed.ws",
    "baxomale.ht.cx", "beefmilk.com", "belledemusique.com",
    "bestchoiceusedcar.com", "bit-degree.com", "bko.kiev.ua",
    "blankenship.website", "bloggers.com", "bluebottle.com",
    "bnote.com", "bongobongo.ml", "boun.cr", "boxomail.lt",
    "brturbo.com.br", "bu.mintemail.com", "c2.hu", "cachedot.net",
    "caramail.com", "cartelera.org", "casa.click", "casualdx.com",
    "centermail.com", "centermail.net", "chogmail.com", "choicemail.com",
    "cialissvr.com", "clixser.com", "cmail.com", "coldmail.com",
    "comparesoftware.tech", "comwest.de", "cookies.org",
    "courrieltemporaire.com", "cubicgroup.org", "currant.ovh",
    "cutout.club", "cybersex.com", "daryxfox.net", "deadaddress.com",
    "deadspam.com", "despam.it", "despammed.com", "devnullmail.com",
    "dfgh.net", "digitalsanctuary.com", "discard.email", "discardmail.com",
    "discardmail.de", "doanart.com", "dogmail.co.uk", "dolphinnet.net",
    "domforfb1.tk", "domforfb2.tk", "domforfb3.tk", "domforfb4.tk",
    "domforfb5.tk", "domforfb6.tk", "domforfb7.tk", "domforfb8.tk",
    "dontreg.com", "dontsendmespam.de", "dot-ml.ml", "dotmsg.com",
    "dr69.site", "drdrb.net", "dspamfree.com", "duam.net", "dumpyemail.com",
    "e-mail.com", "e-mail.org", "e4ward.com", "easytrashmail.com",
    "elitevpnlab.com", "email-fake.com", "email.cbes.net",
    "emailcorner.net", "emaillime.com", "emailmiser.com", "emailondeck.com",
    "emailpinoy.com", "emails.ga", "emails.ink", "emailskip.com",
    "emailspam.pro", "emailthe.net", "emailtmp.com", "emailto.de",
    "emailwarden.com", "emailxemail.com", "emailz.cf", "emailz.ga",
    "emailz.gq", "emailz.ml", "emial.com", "emil.com", "enterto.com",
    "ephemail.net", "ero-tube.org", "etranquil.com", "etranquil.net",
    "etranquil.org", "everyone.net", "explodemail.com", "fake-mail.tk",
    "fakeinbox.com", "fakemail.com", "fakemail.fr", "fakemail.net",
    "fakemails.net", "fakemailz.com", "fammix.com", "fan.net",
    "fanswap.com", "fastacura.com", "fastchevy.com", "fastchrysler.com",
    "fastkawasaki.com", "fastmazda.com", "fastmitsubishi.com",
    "fastnissan.com", "fastsubaru.com", "fastsuzuki.com", "fasttoyota.com",
    "fastyamaha.com", "fatflap.com", "fbma.tk", "fettometern.com",
    "fictionsite.com", "fightallspam.com", "filzmail.com", "fixmail.tk",
    "fizmail.com", "flurred.com", "flyspam.com", "forgetmail.com",
    "fr33mail.info", "frapmail.com", "free-email.ga", "freebabysittercam.com",
    "freeblackboobies.com", "freecat.net", "freeemail.onl",
    "freehotmail.net", "freenet.com", "freeplumpervideos.com",
    "freeschoolgirlvids.com", "freeservers.com", "fuckyou.ooo",
    "gaf.osequent.com", "gamail.top", "garbage.com", "garrymccooey.com",
    "gav0.com", "gexik.com", "gizproject.org", "glitch.sx", "globaleuro.net",
    "glubex.com", "glypx.com", "goemailgo.com", "golemico.com",
    "gorillaswithdirtyarmpits.com", "gothere.biz", "graffiti.net",
    "greensloth.com", "griuc.schule", "grr.la", "gsrv.co.uk",
    "guerillamail.info", "guerillamail.biz", "guerillamail.com",
    "guerillamail.net", "guerillamail.org", "guerrillamail.biz",
    "guerrillamail.de", "guerrillamail.net", "guerrillamail.org",
    "h.mintemail.com", "h8s.org", "haltospam.com", "hbxr.xyz",
    "healyourself.xyz", "hidebusiness.xyz", "hix.kr", "hobbybungalow.eu",
    "homail.com", "hooohush.ai", "hotpop.com", "huangniu8.com",
    "huguesb.ovh", "hulapla.de", "humn.ws.gy", "ieatspam.eu",
    "ieatspam.info", "ignoremail.com", "ihateyoualot.info", "iheartspam.org",
    "imails.info", "iname.com", "inboxbear.com", "inboxed.pw",
    "inboxproxy.com", "incognitomail.com", "incognitomail.net",
    "incognitomail.org", "indigobook.com", "indonix.net", "info-radio.ml",
    "inohide.net", "instant-mail.de", "instantemailaddress.com",
    "ip6.li", "ipoo.org", "irish2me.com", "iwi.net", "jafps.com",
    "jet-express.com.ua", "jmail.fr.nf", "jmail.ovh", "jourrapide.com",
    "jsrsolutions.com", "junk1e.com", "kasmail.com", "kaspop.com",
    "kebi.com", "keinpardon.de", "kennedy808.com", "kiani.com",
    "killmail.com", "killmail.net", "kingyslmail.com", "kiois.com",
    "kksm.be", "klipschx12.com", "kms.my", "kulturbetrieb.info",
    "kurzepost.de", "lags.us", "landmail.co", "lastmail.co",
    "lawlita.com", "lazyinbox.com", "lazyinbox.us", "letmeinonthis.com",
    "letthemeatspam.com", "lillemap.net", "listsail.net", "litedrop.com",
    "liveradio.tk", "lmc220.com", "loash.net", "localgenius.business",
    "lol.com", "lolfreak.net", "lookugly.com", "lopl.co.cc",
    "lortemail.dk", "lovemeet.faith", "lr78.com", "lroid.com",
    "lukop.dk", "m21.cc", "mail-filter.com", "mail-temp.com",
    "mail.aws910.com", "mail.backflip.org", "mail.bccto.me",
    "mail.dataless.ga", "mail.ez.lv", "mail.fast10s.design",
    "mail.fettometern.com", "mail.hotmail.com", "mail.msaging.com",
    "mail.by", "mail0.ga", "mail1.drama.tw", "mail114.net",
    "mail1a.de", "mail21.cc", "mail22.club", "mail2rss.org",
    "mail333.com", "mail4trash.com", "mail4you.usa.cc",
    "mail666.ru", "mail7.org", "mail707.com", "mail8.org",
    "mailadadad.org", "mailback.com", "mailbidon.com", "mailbiz.biz",
    "mailblocks.com", "mailbucket.org", "mailcat.biz", "mailcatch.com",
    "mailcom.com", "mailde.de", "mailde.info", "maildrop.com",
    "maileater.com", "mailexpire.com", "mailfa.tk", "mailforspam.com",
    "mailfree.ga", "mailfree.gq", "mailfree.ml", "mailfreeonline.com",
    "mailfs.com", "mailhaven.com", "mailhex.com", "mailhood.com",
    "mailimate.com", "mailin8r.com", "mailinatar.com", "mailinater.com",
    "mailinator.co.uk", "mailinator.com", "mailinator.gq",
    "mailinator.info", "mailinator.net", "mailinator.org",
    "mailinator.us", "mailinator2.com", "mailincubator.com",
    "mailismagic.com", "mailjunk.org", "mailmate.com", "mailme24.com",
    "mailmetrash.com", "mailmoat.com", "mailmoth.com", "mailnator.com",
    "mailnesia.com", "mailnull.com", "mailops.com", "mailorg.org",
    "mailox.fun", "mailpick.biz", "mailpooch.com", "mailproxsy.com",
    "mailquack.com", "mailrocket.biz", "mailsac.com", "mailscrap.com",
    "mailseal.de", "mailshell.com", "mailshiv.com", "mailsiphon.com",
    "mailslapping.com", "mailslite.com", "mailspam.xyz", "mailtemp.info",
    "mailtemporaire.com", "mailtemporaire.fr", "mailthunder.ml",
    "mailtome.de", "mailtothis.com", "mailtrash.net", "mailtv.net",
    "mailtv.tv", "mailverde.ga", "mailwithyou.com", "mailzi.ru",
    "mailzilla.com", "mailzilla.org", "makemetheking.com",
    "manicero.com", "mansiondev.com", "manybrain.com", "mbx.cc",
    "mciek.com", "mega.zik.dj", "meinspamschutz.de", "meltmail.com",
    "message.be", "message.myssa.info", "messagesafe.co",
    "messwiththebestdielikethe.rest", "mhzayt.online", "midcoastcustoms.com",
    "midcoastcustoms.net", "midlertidig.com", "midlertidig.net",
    "mijnhva.nl", "ministry-of-silly-walks.de", "misery.net",
    "misterpinball.com", "mjukglass.nu", "ml8.ca", "moncourrier.fr.nf",
    "monemail.fr.nf", "monmail.fr.nf", "monumentmail.com", "mopsent.com",
    "mox.pp.ua", "msa.minsmail.com", "msgsafe.ninja", "mt2009.com",
    "mtmdev.com", "mu12.xyz", "muehlacker.tk", "muell.icu",
    "muellmail.com", "munoubengoshi.gq", "my10minutemail.com",
    "myaddy.net", "mycard.net.ua", "mycleaninbox.net",
    "myemail.net", "myemail.net", "mykcm.com", "myletter.online",
    "mymail-in.net", "mymailoasis.com", "mynet.com", "mynetaddress.com",
    "myopang.com", "mypacks.net", "mypartyclip.de", "myphantomemail.com",
    "mysamp.de", "myspaceinc.com", "myspamless.com", "mytrashmail.com",
    "mywarnernet.net", "nailednail.com", "nandb.co.za", "nbtv.org",
    "negated.com", "neomailbox.com", "nepwk.com", "nervhq.org",
    "netmails.com", "netmails.net", "netricity.nl", "netzipper.net",
    "nevermail.de", "next.ovh", "nincsmail.com", "nincsmail.hu",
    "nnh.com", "nnot.net", "nomail.pw", "nomail.xl.cx", "nomorespam.com",
    "nospam.ze.tc", "nospam4.us", "nospamfor.us", "nospamme.com",
    "nowmymail.com", "ntlhelp.net", "nubescontrol.com", "nullbox.info",
    "nurfuerspam.de", "nwldx.com", "o2stk.org", "odnorazovoe.ru",
    "office-email.com", "offpe.com", "ohdomain.com", "ohi.tw",
    "omail.pro", "one-time.email", "oneoffemail.com", "oneoffmail.com",
    "onewaymail.com", "onlatedotcom.info", "onmail.win", "onqin.xyz",
    "ontyne.biz", "opentrash.net", "opmmedia.ga", "origin.xyz",
    "outlook.sk", "ovamail.net", "ovenmail.com",
    "oxfarm1.com", "ozost.com", "pakadebu.ga", "paplease.com",
    "parisannonce.com", "pcapps.xyz", "pcu6.com", "pepbot.com",
    "peppe.usa.cc", "petaloft.com", "pfui.ru", "phrco.de", "pig.pp.ru",
    "piki.si", "pimpedupmyspace.com", "pin-point.ru", "pjjkp.com",
    "plexolan.de", "poczta.onet.pl", "pojok.net", "pokemail.net",
    "politiker.club", "poliusraas.tk", "polyfaust.com", "pookmail.com",
    "poopmail.com", "poormail.com", "pop3.xyz", "pororore.ga",
    "postonline.me", "poutine.xyz", "privacy-mail.net",
    "privacy.net", "privy-mail.com", "privymail.de", "proxymail.eu",
    "prtnx.com", "prtz.eu", "psoxs.com", "punkass.com", "purple.iguana",
    "put2.net", "puttanamail.com", "qacquire.com", "qasti.com",
    "qbfree.us", "qisdo.com", "qisoa.com", "qoika.com", "qq.my",
    "quickinbox.com", "quickmail.nl", "rcpt.at", "re-gister.com",
    "reallymymail.com", "receiveee.com", "receiveee.net",
    "recode.me", "reconmail.com", "recyclemail.dk", "reddit.usa.cc",
    "redfeathercrow.com", "regbypass.com", "regspaces.tk",
    "rejectmail.com", "reliable-mail.com", "remail.cf", "remail.ga",
    "rhyta.com", "richlistpeople.com", "risingsuntouch.com",
    "rklips.com", "rmqkr.net", "rty.tk", "rumgel.com", "rxtx.us",
    "s0ny.net", "safe-mail.net", "safemail.tk", "sale.craigslist.org",
    "salehi.byethost14.com", "saltyshort.com", "sandelf.de",
    "saynotospams.com", "scatmail.com", "scopty.com", "sd3.in",
    "secmail.pw", "secretarea.net", "seenows.com", "selfdestructingmail.com",
    "sendingspecialflyers.com", "sentai.xyz", "server.ms", "sexmagnet.com",
    "shararmail.com", "sharklasers.com", "shieldedmail.com",
    "shmeriously.com", "shortmail.net", "shotmail.net", "showslow.de",
    "shrib.com", "sibmail.com", "siliwangi.ga", "sin.cl",
    "site.otnolive.com", "sittys.de", "sizzlemctwizzle.com",
    "skeleton-mail.com", "skytrailer.com", "slapsfromlastnight.com",
    "slaskpost.se", "slave-auctions.net", "slippery.email",
    "slopsbox.com", "slushmail.com", "sly.io", "smallker.tk",
    "smap.4next.me", "smapfree24.com", "smapfree24.de",
    "smapfree24.eu", "smapfree24.info", "smapfree24.org",
    "smashmail.de", "smellfear.com", "smellrear.com", "smtp33.com",
    "snakemail.com", "snapunit.com", "sneakemail.com", "sneakmail.de",
    "snkmail.com", "socialfurry.org", "sofimail.com", "sofort-mail.de",
    "sofortmail.de", "softpls.asia", "sogetthis.com", "sohu.com",
    "solvemail.info", "songlist.xyz", "spam.2012-2016.ru",
    "spam.4nmob.ru", "spam.alshorty.space", "spam.care",
    "spam.corpee.com", "spam.deluser.net", "spam.gr",
    "spam.la", "spam.mlsend.com", "spam.net",
    "spam.noms.co", "spam.org.es", "spam.su", "spam4.me",
    "spamail.de", "spamarrest.com", "spamavert.com", "spambob.com",
    "spambob.net", "spambob.org", "spambog.com", "spambog.net",
    "spambog.ru", "spambox.info", "spambox.me", "spambox.org",
    "spambox.us", "spamcannon.com", "spamcannon.net",
    "spamcero.com", "spamcon.org", "spamcorptastic.com",
    "spamcowboy.com", "spamcowboy.net", "spamcowboy.org",
    "spamday.com", "spamdecoy.net", "spameater.org",
    "spamex.com", "spamfighter.de", "spamfree24.com",
    "spamfree24.de", "spamfree24.info", "spamfree24.net",
    "spamfree24.org", "spamgoes.in", "spamgourmet.com",
    "spamhereplease.com", "spamhole.com", "spamify.com",
    "spaminator.de", "spamkill.info", "spaml.com",
    "spamlot.net", "spammotel.com", "spamobox.com",
    "spamoff.de", "spamsalad.in", "spamserver.de", "spamslicer.com",
    "spamspy.com", "spamstack.net", "spamthis.co.uk",
    "spamthisplease.com", "spamtrail.com", "spamtroll.net",
    "spamwc.de", "spamwc.info", "speed.1s.fr",
    "sperma.online", "spikio.com", "spoofmail.de", "squizzy.com",
    "squizzy.de", "sr.ro.lt", "sso-demo.okta.com", "stanford-edu.tk",
    "startfu.com", "steambot.net", "stexsy.com", "stinkefinger.net",
    "stop-my-spam.com", "stopdropandroll.com", "storiqax.com",
    "storj99.com", "streamfly.biz", "streamfly.link", "streetwisemail.com",
    "stuff.munich.com", "styliste.xyz", "sudeepmail.com",
    "suioe.com", "supergreatmail.com", "supermailer.jp",
    "superrito.com", "suremail.info", "surfmail.tk",
    "svxr.org", "sweetxxx.de", "swift10minutemail.com",
    "tafmail.com", "tafmail.net", "tafoi.com", "tagmymedia.com",
    "talkwithstranger.com", "tartapelno.com", "techemail.com",
    "techgroup.me", "teleosaurs.xyz", "teley.info", "tench.xyz",
    "temporaryemail.net", "temporaryinbox.com",
    "temporarymail.org", "temporarymailaddress.com",
    "tempr.email", "ternaklele.ga", "test.com", "test.de",
    "theaviors.com", "thebearshark.com", "thebestremont.ru",
    "thecloudbox.com", "thediamonds.org", "thelightningmail.net",
    "themailpro.net", "thembones.com.au", "themostemail.com",
    "thepaladins.com", "thequickemail.com", "thescrappermovie.com",
    "theteastory.info", "thietbivanphong.vn", "thisisnotmyrealemail.com",
    "thismail.net", "threexmail.com", "throam.com", "thrott.com",
    "throwam.com", "throwaway.email", "throwaway.xyz",
    "throwawayemail.com", "throya.com", "thunkmail.com",
    "tienhuis.nl", "tilien.com", "tittbit.in", "tival.info",
    "tizi.com", "tmail.com", "tmail.ws", "tmail1.xyz",
    "tmmv.net", "tmp.refi64.com", "tmpeml.info", "tmpjr.me",
    "tmpmail.net", "tmpmail.org", "toddsbighug.com", "toiea.com",
    "tokem.co", "tonymanso.com", "toomail.biz", "top101.de",
    "topaddress.net", "topinbox.cf", "topinbox.ga", "topinbox.gq",
    "topinbox.ml", "topranklist.de", "tormail.org",
    "totalvista.com", "toughlife.expert", "trash-amil.com",
    "trash-me.com", "trash2009.com", "trash2010.com",
    "trash2011.com", "trashcanmail.com", "trashdevil.com",
    "trashdevil.de", "trashinbox.net", "trashmail.at",
    "trashmail.com", "trashmail.de", "trashmail.ga",
    "trashmail.gq", "trashmail.me", "trashmail.net",
    "trashmail.org", "trashmail.ws", "trashmailer.com",
    "trashmails.com", "trashspam.com", "trashymail.com",
    "trashymail.net", "trbvm.com", "trbvn.com", "trbvo.com",
    "trialmail.de", "trickmail.net", "trillianpro.com",
    "tropicalbiker.com", "trumpmail.com", "tryalert.com",
    "ttszuo.xyz", "tualias.com", "tugflix.org", "turoid.com",
    "turual.com", "tvchd.com", "tverya.com", "twoanchors.com",
    "tyldd.com", "tyme4.com", "uacro.com", "ubismail.net",
    "ubr.at", "ufacturing.com", "ufgqgrid.xyz", "uggsrock.com",
    "ukr.net", "umail.net", "ummah.org", "unbounded.xyz",
    "unforgettable.ovh", "uni.xyz", "untitled-project.xyz",
    "upc-i.xyz", "upliftnow.com", "uplipht.com", "uploadnolimit.com",
    "upozowac.info", "urfunktion.se", "utilities-online.info",
    "v13.gr", "v8email.com", "validemail.com", "valemail.net",
    "vcmail.com", "vel.xyz", "venompen.com", "ver0.cf", "ver0.ga",
    "ver0.gq", "ver0.ml", "ver0.tk", "vercelli.cf", "vercelli.ga",
    "vercelli.gq", "vercelli.ml", "vercelli.tk", "veryrealemail.com",
    "vfemail.net", "vickaentb.tk", "victime.ninja", "victoriantwins.com",
    "vidchart.com", "viewcastmedia.com", "viewcastmedia.net",
    "vinbazar.com", "vipso.xyz", "viralemail.com", "viroleni.cu.cc",
    "vistomail.com", "vixletdev.com", "vkcode.ru", "vmailing.info",
    "vmani.com", "vmpanda.com", "vnedu.me", "voidbay.com",
    "volaj.com", "voltaer.com", "vomoto.com", "vp.yzar.xyz",
    "vpn.st", "vps30.com", "vps911.net", "vsimcard.com",
    "vubby.com", "vztc.com", "w3internet.co.uk", "walala.org",
    "walkmail.eu", "walkmail.net", "walkmail.ru", "wants.dating",
    "wasteland.rfc822.org", "watch-harry-potter.xyz",
    "watchever.biz", "watchfull.net", "watchironman3onlinefree.com",
    "web-contact.org", "web-email.eu", "web-emailbox.eu",
    "web-mailing.eu", "web0.xyz", "webemail.me", "webm4il.info",
    "webmail.uu.gl", "webuser.in", "wee.my", "wegwerf-emails.de",
    "wegwerfmail.de", "wegwerfmail.info", "wegwerfmail.net",
    "wegwerfmail.org", "wegwerpmailadres.nl", "wegwerpmailadres.nl",
    "wetrainbayarea.com", "wetrainbayarea.org", "wfgdfhj.tk",
    "wh4f.org", "whatiaas.com", "whatifanalytics.com",
    "whatpaas.com", "whatsaas.com", "whiffles.org", "whopy.com",
    "whyspam.me", "wibblesmith.com", "wicked.cricket", "widaryanto.info",
    "wikidnot.com", "willhackforfood.biz", "willselfdestruct.com",
    "wimsg.com", "winemaven.info", "wins.com.br", "wlist.ro",
    "wmail.cf", "wmtek.xyz", "wolfsmail.tk", "wollan.info",
    "worldbeyblade.org", "writeme.com", "wrmail.net", "wronghead.com",
    "ws.gy", "wudet.men", "wuespdj.xyz", "wupics.com", "wuzup.net",
    "wuzupmail.net", "wwwnew.eu", "x1x.spb.ru", "xagloo.com",
    "xcode.ro", "xcompress.com", "xcpy.com", "xemaps.com",
    "xents.com", "xing886.uu.gl", "xmaily.com", "xn--9kq967o.com",
    "xoxox.cc", "xoxy.net", "xperiae5.com", "xrap.de", "xs4all.nu",
    "xsmail.com", "xuno.com", "xwaretech.info", "xwaretech.net",
    "xwaretech.tk", "xww.ro", "xyzfree.net", "xyzmail.ml", "xzapmail.com",
    "y7mail.com", "yabai-oppai-hentai.science", "yahmail.top", "yanet.me",
    "yapped.net", "ycare.de", "yep.it", "yhg.biz", "ynmrealty.com",
    "yogamaven.com", "yomail.info", "yoo.ro", "yopmail.com",
    "yopmail.fr", "yopmail.gq", "yopmail.net", "yopmail.org",
    "yopmail.pp.ua", "yordanmail.cf", "youmail.ga", "youmailr.com",
    "youmails.online", "youneedmore.info", "youpamf.com",
    "your-disposable.com", "yoursuccessful.xyz", "ypmail.webarnak.fr.eu.org",
    "yrmx.xyz", "yuurok.com", "z1p.biz", "z1pg.biz", "za.com",
    "zain.site", "zainmax.net", "zaktouni.fr", "ze.gally.ch",
    "zehnminutenmail.de", "zehnminutenmail.net", "zetmail.com",
    "zippymail.info", "zipsendtest.com", "zoaxe.com", "zoemail.com",
    "zoemail.net", "zoemail.org", "zombie-hive.com", "zomg.info",
    "zumpat.com", "zxcv.com", "zxcvbnm.com", "zzz.com",
    "zzz.com.pl", "zzz.fi",
}

# ── Role-account prefixes ──────────────────────────────────────────────────
ROLE_PREFIXES: set[str] = {
    "info", "sales", "admin", "support", "contact", "help", "team",
    "office", "hello", "careers", "jobs", "no-reply", "noreply",
    "postmaster", "webmaster", "abuse", "billing", "marketing",
    "press", "pr", "media", "editor", "hr", "recruitment",
    "partner", "partners", "newsletter", "news", "feedback",
    "service", "services", "enquiries", "inquiries", "orders",
    "shipping", "delivery", "account", "notifications",
}

# ── Major providers (honesty rule — they lie at SMTP) ──────────────────────
MAJOR_PROVIDER_DOMAINS: set[str] = {
    "gmail.com", "outlook.com", "hotmail.com", "yahoo.com",
    "icloud.com", "protonmail.com", "proton.me", "pm.me",
    "aol.com", "zoho.com", "yandex.com", "gmx.com",
    "mail.com", "fastmail.com", "tutanota.com",
}

# ── MX-host provider patterns (honesty rule by mail host) ──────────────────
# Domains whose MX points to one of these hosts run on a provider that does not
# allow external mailbox verification (greylists/refuses RCPT, or is encrypted-
# only). Detect by substring match on the MX hostname so any custom domain on
# these providers is handled, not just the consumer domain.
MX_PROVIDER_PATTERNS: dict[str, str] = {
    "google.com": "Google Workspace",
    "googlemail.com": "Google Workspace",
    "outlook.com": "Microsoft 365",
    "protection.outlook.com": "Microsoft 365",
    "tutanota.de": "Tutanota (encrypted)",
    "tuta.com": "Tutanota (encrypted)",
    "protonmail.ch": "Proton Mail (encrypted)",
    "proton.me": "Proton Mail (encrypted)",
    "zoho.com": "Zoho",
    "zoho.eu": "Zoho",
    "yahoodns.net": "Yahoo",
    "icloud.com": "iCloud",
    "pphosted.com": "Proofpoint",
    "mimecast.com": "Mimecast",
    "messagelabs.com": "Symantec/Mimecast",
}


# ── Free consumer providers ────────────────────────────────────────────────
FREE_PROVIDER_DOMAINS: set[str] = {
    "gmail.com", "outlook.com", "hotmail.com", "yahoo.com",
    "icloud.com", "protonmail.com", "proton.me", "pm.me",
    "aol.com", "zoho.com", "yandex.com", "gmx.com",
    "mail.com", "fastmail.com", "tutanota.com",
    "live.com", "msn.com", "ymail.com", "rocketmail.com",
    "rediffmail.com", "lycos.com", "mail.ru", "yandex.ru",
    "bk.ru", "inbox.ru", "list.ru",
}


# ── Syntax check ───────────────────────────────────────────────────────────
def syntax_check(email: str) -> tuple[bool, str]:
    """
    Validate email syntax using Python's email module + regex.
    Returns (is_valid, normalized_or_reason).
    """
    if not email or not isinstance(email, str):
        return False, ""
    # Remove leading/trailing whitespace
    email = email.strip()
    if not email:
        return False, ""
    # Use parseaddr — it returns (realname, email_addr)
    _, parsed = parseaddr(email)
    if not parsed or "@" not in parsed:
        return False, ""
    # Basic structural regex (simpler than full RFC 5322, catches common issues)
    # This is a pragmatic check that catches >99% of bad addresses
    local, domain = parsed.rsplit("@", 1)
    if not local or not domain:
        return False, ""
    if len(local) > 64 or len(domain) > 255:
        return False, ""
    if len(parsed) > 254:
        return False, ""
    # Check for common syntax errors
    if ".." in local:
        return False, ""
    # Domain must have at least one dot (or be localhost for testing)
    if "." not in domain and domain != "localhost":
        return False, ""
    # Check domain part
    domain_re = re.compile(
        r'^([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$'
    )
    if not domain_re.match(domain):
        return False, ""
    return True, parsed.lower()


# ── Disposable domain check ────────────────────────────────────────────────
def is_disposable_domain(domain: str) -> bool:
    """Check if domain is a known disposable email provider."""
    return domain.lower() in DISPOSABLE_DOMAINS


# ── Role account check ─────────────────────────────────────────────────────
def is_role_account(local_part: str) -> bool:
    """Check if the local part is a common role/function address."""
    local_lower = local_part.lower().strip()
    # Check exact match
    if local_lower in ROLE_PREFIXES:
        return True
    # Check prefix match with a separator boundary (e.g. "sales-team", "info.uk").
    # Bare startswith would flag real names ("priya" via "pr", "newsom" via "news").
    for prefix in ROLE_PREFIXES:
        if local_lower.startswith(prefix) and len(local_lower) > len(prefix):
            if local_lower[len(prefix)] in "-._+":
                return True
    return False


# ── Major provider check ───────────────────────────────────────────────────
def is_major_provider(domain: str) -> bool:
    """Check if domain is a major provider that lies at SMTP."""
    return domain.lower() in MAJOR_PROVIDER_DOMAINS


# ── Free provider check ────────────────────────────────────────────────────
def is_free_provider(domain: str) -> bool:
    """Check if domain is a free consumer provider."""
    return domain.lower() in FREE_PROVIDER_DOMAINS


# ── MX-host provider detection (honesty rule by mail host) ─────────────────
def detect_mx_provider(mx_hosts: list[str]) -> str | None:
    """
    Inspect resolved MX hostnames. If they belong to a provider that blocks
    external mailbox verification, return the provider name; else None.
    Substring match so e.g. "aspmx.l.google.com" -> Google Workspace.
    """
    for host in mx_hosts:
        host_lower = host.lower().rstrip(".")
        for pattern, provider in MX_PROVIDER_PATTERNS.items():
            if host_lower == pattern or host_lower.endswith("." + pattern):
                return provider
    return None


# ── MX DNS lookup ──────────────────────────────────────────────────────────
def resolve_mx(domain: str) -> list[str] | None:
    """
    Resolve MX records for a domain.
    Returns sorted list of MX hostnames (by priority) or None if no MX records.
    """
    try:
        answers = dns.resolver.resolve(domain, "MX", lifetime=5)
        if not answers:
            return None
        # Sort by priority (preference value)
        mx_records = sorted(
            [(int(r.preference), str(r.exchange).rstrip(".")) for r in answers],
            key=lambda x: x[0],
        )
        return [host for _, host in mx_records]
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN,
            dns.resolver.NoNameservers, dns.exception.Timeout,
            dns.resolver.YXDOMAIN):
        return None
    except Exception as exc:
        logger.debug("MX lookup error for %s: %s", domain, exc)
        return None


# ── Catch-all probe ────────────────────────────────────────────────────────
def _generate_random_local() -> str:
    """Generate a random local part for catch-all probing."""
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=12))


def probe_catch_all(mx_host: str, domain: str, timeout_seconds: float = 5.0) -> bool:
    """
    Probe a domain for catch-all behavior by attempting RCPT TO on a
    non-existent address. Returns True if domain is catch-all, False otherwise.
    """
    random_local = _generate_random_local()
    test_email = f"{random_local}@{domain}"

    try:
        with smtplib.SMTP(timeout=timeout_seconds) as smtp:
            smtp.connect(mx_host, 25, timeout=timeout_seconds)
            smtp.ehlo_or_helo_if_needed()
            # Empty MAIL FROM (<>) per RFC 5321 verification convention.
            smtp.mail("")
            code, _ = smtp.rcpt(test_email)
            # 250 = accepted → catch-all
            return code == 250
    except Exception:
        return False


# ── SMTP verification ──────────────────────────────────────────────────────
def smtp_verify_sync(email: str, mx_host: str, timeout_seconds: float = 5.0) -> bool | None:
    """
    Synchronous SMTP verification against one MX host.
    Returns True (valid), False (invalid), or None (unknown/temp failure).
    """
    # Extract local part and domain for MAIL FROM
    _, parsed = parseaddr(email)
    if not parsed:
        return None
    local, domain = parsed.rsplit("@", 1)

    try:
        with smtplib.SMTP(timeout=timeout_seconds) as smtp:
            smtp.connect(mx_host, 25, timeout=timeout_seconds)
            smtp.ehlo_or_helo_if_needed()

            # Empty MAIL FROM (<>) per RFC 5321 verification convention.
            smtp.mail("")
            rcpt_code, rcpt_msg = smtp.rcpt(email)

            # 250 = mailbox exists (valid)
            if rcpt_code == 250:
                return True

            # 5xx = does not exist (invalid)
            # Common codes: 550, 551, 552, 553, 554
            if 500 <= rcpt_code < 600:
                return False

            # 4xx = temp fail (unknown)
            if 400 <= rcpt_code < 500:
                return None

            # Any other code → unknown
            return None

    except (smtplib.SMTPServerDisconnected, smtplib.SMTPConnectError,
            smtplib.SMTPHeloError, smtplib.SMTPException,
            ConnectionRefusedError, TimeoutError, OSError):
        return None
