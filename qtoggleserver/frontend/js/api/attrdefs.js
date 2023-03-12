/**
 * @namespace qtoggle.api.attrdefs
 */

import {gettext}           from '$qui/base/i18n.js'
import {PasswordField}     from '$qui/forms/common-fields/common-fields.js'
import {ProgressDiskField} from '$qui/forms/common-fields/common-fields.js'
import {TextAreaField}     from '$qui/forms/common-fields/common-fields.js'
import {TextField}         from '$qui/forms/common-fields/common-fields.js'
import * as DateUtils      from '$qui/utils/date.js'
import * as ObjectUtils    from '$qui/utils/object.js'
import * as StringUtils    from '$qui/utils/string.js'

import {netmaskFromLen} from '$app/utils.js'
import {netmaskToLen}   from '$app/utils.js'

import {ConfigNameField}         from './attrdef-fields.js'
import {WiFiSignalStrengthField} from './attrdef-fields.js'


const IP_ADDRESS_PATTERN = /^([0-9]{1,3}\.){3}[0-9]{1,3}$/
const DATE_PATTERN = /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/

const TIMEZONE_CHOICES = [
    {display_name: 'Africa/Abidjan', value: 'Africa/Abidjan'},
    {display_name: 'Africa/Accra', value: 'Africa/Accra'},
    {display_name: 'Africa/Addis_Ababa', value: 'Africa/Addis_Ababa'},
    {display_name: 'Africa/Algiers', value: 'Africa/Algiers'},
    {display_name: 'Africa/Asmara', value: 'Africa/Asmara'},
    {display_name: 'Africa/Bamako', value: 'Africa/Bamako'},
    {display_name: 'Africa/Bangui', value: 'Africa/Bangui'},
    {display_name: 'Africa/Banjul', value: 'Africa/Banjul'},
    {display_name: 'Africa/Bissau', value: 'Africa/Bissau'},
    {display_name: 'Africa/Blantyre', value: 'Africa/Blantyre'},
    {display_name: 'Africa/Brazzaville', value: 'Africa/Brazzaville'},
    {display_name: 'Africa/Bujumbura', value: 'Africa/Bujumbura'},
    {display_name: 'Africa/Cairo', value: 'Africa/Cairo'},
    {display_name: 'Africa/Casablanca', value: 'Africa/Casablanca'},
    {display_name: 'Africa/Ceuta', value: 'Africa/Ceuta'},
    {display_name: 'Africa/Conakry', value: 'Africa/Conakry'},
    {display_name: 'Africa/Dakar', value: 'Africa/Dakar'},
    {display_name: 'Africa/Dar_es_Salaam', value: 'Africa/Dar_es_Salaam'},
    {display_name: 'Africa/Djibouti', value: 'Africa/Djibouti'},
    {display_name: 'Africa/Douala', value: 'Africa/Douala'},
    {display_name: 'Africa/El_Aaiun', value: 'Africa/El_Aaiun'},
    {display_name: 'Africa/Freetown', value: 'Africa/Freetown'},
    {display_name: 'Africa/Gaborone', value: 'Africa/Gaborone'},
    {display_name: 'Africa/Harare', value: 'Africa/Harare'},
    {display_name: 'Africa/Johannesburg', value: 'Africa/Johannesburg'},
    {display_name: 'Africa/Juba', value: 'Africa/Juba'},
    {display_name: 'Africa/Kampala', value: 'Africa/Kampala'},
    {display_name: 'Africa/Khartoum', value: 'Africa/Khartoum'},
    {display_name: 'Africa/Kigali', value: 'Africa/Kigali'},
    {display_name: 'Africa/Kinshasa', value: 'Africa/Kinshasa'},
    {display_name: 'Africa/Lagos', value: 'Africa/Lagos'},
    {display_name: 'Africa/Libreville', value: 'Africa/Libreville'},
    {display_name: 'Africa/Lome', value: 'Africa/Lome'},
    {display_name: 'Africa/Luanda', value: 'Africa/Luanda'},
    {display_name: 'Africa/Lubumbashi', value: 'Africa/Lubumbashi'},
    {display_name: 'Africa/Lusaka', value: 'Africa/Lusaka'},
    {display_name: 'Africa/Malabo', value: 'Africa/Malabo'},
    {display_name: 'Africa/Maputo', value: 'Africa/Maputo'},
    {display_name: 'Africa/Maseru', value: 'Africa/Maseru'},
    {display_name: 'Africa/Mbabane', value: 'Africa/Mbabane'},
    {display_name: 'Africa/Mogadishu', value: 'Africa/Mogadishu'},
    {display_name: 'Africa/Monrovia', value: 'Africa/Monrovia'},
    {display_name: 'Africa/Nairobi', value: 'Africa/Nairobi'},
    {display_name: 'Africa/Ndjamena', value: 'Africa/Ndjamena'},
    {display_name: 'Africa/Niamey', value: 'Africa/Niamey'},
    {display_name: 'Africa/Nouakchott', value: 'Africa/Nouakchott'},
    {display_name: 'Africa/Ouagadougou', value: 'Africa/Ouagadougou'},
    {display_name: 'Africa/Porto-Novo', value: 'Africa/Porto-Novo'},
    {display_name: 'Africa/Sao_Tome', value: 'Africa/Sao_Tome'},
    {display_name: 'Africa/Tripoli', value: 'Africa/Tripoli'},
    {display_name: 'Africa/Tunis', value: 'Africa/Tunis'},
    {display_name: 'Africa/Windhoek', value: 'Africa/Windhoek'},
    {display_name: 'America/Adak', value: 'America/Adak'},
    {display_name: 'America/Anchorage', value: 'America/Anchorage'},
    {display_name: 'America/Anguilla', value: 'America/Anguilla'},
    {display_name: 'America/Antigua', value: 'America/Antigua'},
    {display_name: 'America/Araguaina', value: 'America/Araguaina'},
    {display_name: 'America/Argentina/Buenos_Aires', value: 'America/Argentina/Buenos_Aires'},
    {display_name: 'America/Argentina/Catamarca', value: 'America/Argentina/Catamarca'},
    {display_name: 'America/Argentina/Cordoba', value: 'America/Argentina/Cordoba'},
    {display_name: 'America/Argentina/Jujuy', value: 'America/Argentina/Jujuy'},
    {display_name: 'America/Argentina/La_Rioja', value: 'America/Argentina/La_Rioja'},
    {display_name: 'America/Argentina/Mendoza', value: 'America/Argentina/Mendoza'},
    {display_name: 'America/Argentina/Rio_Gallegos', value: 'America/Argentina/Rio_Gallegos'},
    {display_name: 'America/Argentina/Salta', value: 'America/Argentina/Salta'},
    {display_name: 'America/Argentina/San_Juan', value: 'America/Argentina/San_Juan'},
    {display_name: 'America/Argentina/San_Luis', value: 'America/Argentina/San_Luis'},
    {display_name: 'America/Argentina/Tucuman', value: 'America/Argentina/Tucuman'},
    {display_name: 'America/Argentina/Ushuaia', value: 'America/Argentina/Ushuaia'},
    {display_name: 'America/Aruba', value: 'America/Aruba'},
    {display_name: 'America/Asuncion', value: 'America/Asuncion'},
    {display_name: 'America/Atikokan', value: 'America/Atikokan'},
    {display_name: 'America/Bahia', value: 'America/Bahia'},
    {display_name: 'America/Bahia_Banderas', value: 'America/Bahia_Banderas'},
    {display_name: 'America/Barbados', value: 'America/Barbados'},
    {display_name: 'America/Belem', value: 'America/Belem'},
    {display_name: 'America/Belize', value: 'America/Belize'},
    {display_name: 'America/Blanc-Sablon', value: 'America/Blanc-Sablon'},
    {display_name: 'America/Boa_Vista', value: 'America/Boa_Vista'},
    {display_name: 'America/Bogota', value: 'America/Bogota'},
    {display_name: 'America/Boise', value: 'America/Boise'},
    {display_name: 'America/Cambridge_Bay', value: 'America/Cambridge_Bay'},
    {display_name: 'America/Campo_Grande', value: 'America/Campo_Grande'},
    {display_name: 'America/Cancun', value: 'America/Cancun'},
    {display_name: 'America/Caracas', value: 'America/Caracas'},
    {display_name: 'America/Cayenne', value: 'America/Cayenne'},
    {display_name: 'America/Cayman', value: 'America/Cayman'},
    {display_name: 'America/Chicago', value: 'America/Chicago'},
    {display_name: 'America/Chihuahua', value: 'America/Chihuahua'},
    {display_name: 'America/Costa_Rica', value: 'America/Costa_Rica'},
    {display_name: 'America/Creston', value: 'America/Creston'},
    {display_name: 'America/Cuiaba', value: 'America/Cuiaba'},
    {display_name: 'America/Curacao', value: 'America/Curacao'},
    {display_name: 'America/Danmarkshavn', value: 'America/Danmarkshavn'},
    {display_name: 'America/Dawson', value: 'America/Dawson'},
    {display_name: 'America/Dawson_Creek', value: 'America/Dawson_Creek'},
    {display_name: 'America/Denver', value: 'America/Denver'},
    {display_name: 'America/Detroit', value: 'America/Detroit'},
    {display_name: 'America/Dominica', value: 'America/Dominica'},
    {display_name: 'America/Edmonton', value: 'America/Edmonton'},
    {display_name: 'America/Eirunepe', value: 'America/Eirunepe'},
    {display_name: 'America/El_Salvador', value: 'America/El_Salvador'},
    {display_name: 'America/Fort_Nelson', value: 'America/Fort_Nelson'},
    {display_name: 'America/Fortaleza', value: 'America/Fortaleza'},
    {display_name: 'America/Glace_Bay', value: 'America/Glace_Bay'},
    {display_name: 'America/Goose_Bay', value: 'America/Goose_Bay'},
    {display_name: 'America/Grand_Turk', value: 'America/Grand_Turk'},
    {display_name: 'America/Grenada', value: 'America/Grenada'},
    {display_name: 'America/Guadeloupe', value: 'America/Guadeloupe'},
    {display_name: 'America/Guatemala', value: 'America/Guatemala'},
    {display_name: 'America/Guayaquil', value: 'America/Guayaquil'},
    {display_name: 'America/Guyana', value: 'America/Guyana'},
    {display_name: 'America/Halifax', value: 'America/Halifax'},
    {display_name: 'America/Havana', value: 'America/Havana'},
    {display_name: 'America/Hermosillo', value: 'America/Hermosillo'},
    {display_name: 'America/Indiana/Indianapolis', value: 'America/Indiana/Indianapolis'},
    {display_name: 'America/Indiana/Knox', value: 'America/Indiana/Knox'},
    {display_name: 'America/Indiana/Marengo', value: 'America/Indiana/Marengo'},
    {display_name: 'America/Indiana/Petersburg', value: 'America/Indiana/Petersburg'},
    {display_name: 'America/Indiana/Tell_City', value: 'America/Indiana/Tell_City'},
    {display_name: 'America/Indiana/Vevay', value: 'America/Indiana/Vevay'},
    {display_name: 'America/Indiana/Vincennes', value: 'America/Indiana/Vincennes'},
    {display_name: 'America/Indiana/Winamac', value: 'America/Indiana/Winamac'},
    {display_name: 'America/Inuvik', value: 'America/Inuvik'},
    {display_name: 'America/Iqaluit', value: 'America/Iqaluit'},
    {display_name: 'America/Jamaica', value: 'America/Jamaica'},
    {display_name: 'America/Juneau', value: 'America/Juneau'},
    {display_name: 'America/Kentucky/Louisville', value: 'America/Kentucky/Louisville'},
    {display_name: 'America/Kentucky/Monticello', value: 'America/Kentucky/Monticello'},
    {display_name: 'America/Kralendijk', value: 'America/Kralendijk'},
    {display_name: 'America/La_Paz', value: 'America/La_Paz'},
    {display_name: 'America/Lima', value: 'America/Lima'},
    {display_name: 'America/Los_Angeles', value: 'America/Los_Angeles'},
    {display_name: 'America/Lower_Princes', value: 'America/Lower_Princes'},
    {display_name: 'America/Maceio', value: 'America/Maceio'},
    {display_name: 'America/Managua', value: 'America/Managua'},
    {display_name: 'America/Manaus', value: 'America/Manaus'},
    {display_name: 'America/Marigot', value: 'America/Marigot'},
    {display_name: 'America/Martinique', value: 'America/Martinique'},
    {display_name: 'America/Matamoros', value: 'America/Matamoros'},
    {display_name: 'America/Mazatlan', value: 'America/Mazatlan'},
    {display_name: 'America/Menominee', value: 'America/Menominee'},
    {display_name: 'America/Merida', value: 'America/Merida'},
    {display_name: 'America/Metlakatla', value: 'America/Metlakatla'},
    {display_name: 'America/Mexico_City', value: 'America/Mexico_City'},
    {display_name: 'America/Miquelon', value: 'America/Miquelon'},
    {display_name: 'America/Moncton', value: 'America/Moncton'},
    {display_name: 'America/Monterrey', value: 'America/Monterrey'},
    {display_name: 'America/Montevideo', value: 'America/Montevideo'},
    {display_name: 'America/Montserrat', value: 'America/Montserrat'},
    {display_name: 'America/Nassau', value: 'America/Nassau'},
    {display_name: 'America/New_York', value: 'America/New_York'},
    {display_name: 'America/Nipigon', value: 'America/Nipigon'},
    {display_name: 'America/Nome', value: 'America/Nome'},
    {display_name: 'America/Noronha', value: 'America/Noronha'},
    {display_name: 'America/North_Dakota/Beulah', value: 'America/North_Dakota/Beulah'},
    {display_name: 'America/North_Dakota/Center', value: 'America/North_Dakota/Center'},
    {display_name: 'America/North_Dakota/New_Salem', value: 'America/North_Dakota/New_Salem'},
    {display_name: 'America/Nuuk', value: 'America/Nuuk'},
    {display_name: 'America/Ojinaga', value: 'America/Ojinaga'},
    {display_name: 'America/Panama', value: 'America/Panama'},
    {display_name: 'America/Pangnirtung', value: 'America/Pangnirtung'},
    {display_name: 'America/Paramaribo', value: 'America/Paramaribo'},
    {display_name: 'America/Phoenix', value: 'America/Phoenix'},
    {display_name: 'America/Port-au-Prince', value: 'America/Port-au-Prince'},
    {display_name: 'America/Port_of_Spain', value: 'America/Port_of_Spain'},
    {display_name: 'America/Porto_Velho', value: 'America/Porto_Velho'},
    {display_name: 'America/Puerto_Rico', value: 'America/Puerto_Rico'},
    {display_name: 'America/Punta_Arenas', value: 'America/Punta_Arenas'},
    {display_name: 'America/Rainy_River', value: 'America/Rainy_River'},
    {display_name: 'America/Rankin_Inlet', value: 'America/Rankin_Inlet'},
    {display_name: 'America/Recife', value: 'America/Recife'},
    {display_name: 'America/Regina', value: 'America/Regina'},
    {display_name: 'America/Resolute', value: 'America/Resolute'},
    {display_name: 'America/Rio_Branco', value: 'America/Rio_Branco'},
    {display_name: 'America/Santarem', value: 'America/Santarem'},
    {display_name: 'America/Santiago', value: 'America/Santiago'},
    {display_name: 'America/Santo_Domingo', value: 'America/Santo_Domingo'},
    {display_name: 'America/Sao_Paulo', value: 'America/Sao_Paulo'},
    {display_name: 'America/Scoresbysund', value: 'America/Scoresbysund'},
    {display_name: 'America/Sitka', value: 'America/Sitka'},
    {display_name: 'America/St_Barthelemy', value: 'America/St_Barthelemy'},
    {display_name: 'America/St_Johns', value: 'America/St_Johns'},
    {display_name: 'America/St_Kitts', value: 'America/St_Kitts'},
    {display_name: 'America/St_Lucia', value: 'America/St_Lucia'},
    {display_name: 'America/St_Thomas', value: 'America/St_Thomas'},
    {display_name: 'America/St_Vincent', value: 'America/St_Vincent'},
    {display_name: 'America/Swift_Current', value: 'America/Swift_Current'},
    {display_name: 'America/Tegucigalpa', value: 'America/Tegucigalpa'},
    {display_name: 'America/Thule', value: 'America/Thule'},
    {display_name: 'America/Thunder_Bay', value: 'America/Thunder_Bay'},
    {display_name: 'America/Tijuana', value: 'America/Tijuana'},
    {display_name: 'America/Toronto', value: 'America/Toronto'},
    {display_name: 'America/Tortola', value: 'America/Tortola'},
    {display_name: 'America/Vancouver', value: 'America/Vancouver'},
    {display_name: 'America/Whitehorse', value: 'America/Whitehorse'},
    {display_name: 'America/Winnipeg', value: 'America/Winnipeg'},
    {display_name: 'America/Yakutat', value: 'America/Yakutat'},
    {display_name: 'America/Yellowknife', value: 'America/Yellowknife'},
    {display_name: 'Antarctica/Casey', value: 'Antarctica/Casey'},
    {display_name: 'Antarctica/Davis', value: 'Antarctica/Davis'},
    {display_name: 'Antarctica/DumontDUrville', value: 'Antarctica/DumontDUrville'},
    {display_name: 'Antarctica/Macquarie', value: 'Antarctica/Macquarie'},
    {display_name: 'Antarctica/Mawson', value: 'Antarctica/Mawson'},
    {display_name: 'Antarctica/McMurdo', value: 'Antarctica/McMurdo'},
    {display_name: 'Antarctica/Palmer', value: 'Antarctica/Palmer'},
    {display_name: 'Antarctica/Rothera', value: 'Antarctica/Rothera'},
    {display_name: 'Antarctica/Syowa', value: 'Antarctica/Syowa'},
    {display_name: 'Antarctica/Troll', value: 'Antarctica/Troll'},
    {display_name: 'Antarctica/Vostok', value: 'Antarctica/Vostok'},
    {display_name: 'Arctic/Longyearbyen', value: 'Arctic/Longyearbyen'},
    {display_name: 'Asia/Aden', value: 'Asia/Aden'},
    {display_name: 'Asia/Almaty', value: 'Asia/Almaty'},
    {display_name: 'Asia/Amman', value: 'Asia/Amman'},
    {display_name: 'Asia/Anadyr', value: 'Asia/Anadyr'},
    {display_name: 'Asia/Aqtau', value: 'Asia/Aqtau'},
    {display_name: 'Asia/Aqtobe', value: 'Asia/Aqtobe'},
    {display_name: 'Asia/Ashgabat', value: 'Asia/Ashgabat'},
    {display_name: 'Asia/Atyrau', value: 'Asia/Atyrau'},
    {display_name: 'Asia/Baghdad', value: 'Asia/Baghdad'},
    {display_name: 'Asia/Bahrain', value: 'Asia/Bahrain'},
    {display_name: 'Asia/Baku', value: 'Asia/Baku'},
    {display_name: 'Asia/Bangkok', value: 'Asia/Bangkok'},
    {display_name: 'Asia/Barnaul', value: 'Asia/Barnaul'},
    {display_name: 'Asia/Beirut', value: 'Asia/Beirut'},
    {display_name: 'Asia/Bishkek', value: 'Asia/Bishkek'},
    {display_name: 'Asia/Brunei', value: 'Asia/Brunei'},
    {display_name: 'Asia/Chita', value: 'Asia/Chita'},
    {display_name: 'Asia/Choibalsan', value: 'Asia/Choibalsan'},
    {display_name: 'Asia/Colombo', value: 'Asia/Colombo'},
    {display_name: 'Asia/Damascus', value: 'Asia/Damascus'},
    {display_name: 'Asia/Dhaka', value: 'Asia/Dhaka'},
    {display_name: 'Asia/Dili', value: 'Asia/Dili'},
    {display_name: 'Asia/Dubai', value: 'Asia/Dubai'},
    {display_name: 'Asia/Dushanbe', value: 'Asia/Dushanbe'},
    {display_name: 'Asia/Famagusta', value: 'Asia/Famagusta'},
    {display_name: 'Asia/Gaza', value: 'Asia/Gaza'},
    {display_name: 'Asia/Hebron', value: 'Asia/Hebron'},
    {display_name: 'Asia/Ho_Chi_Minh', value: 'Asia/Ho_Chi_Minh'},
    {display_name: 'Asia/Hong_Kong', value: 'Asia/Hong_Kong'},
    {display_name: 'Asia/Hovd', value: 'Asia/Hovd'},
    {display_name: 'Asia/Irkutsk', value: 'Asia/Irkutsk'},
    {display_name: 'Asia/Jakarta', value: 'Asia/Jakarta'},
    {display_name: 'Asia/Jayapura', value: 'Asia/Jayapura'},
    {display_name: 'Asia/Jerusalem', value: 'Asia/Jerusalem'},
    {display_name: 'Asia/Kabul', value: 'Asia/Kabul'},
    {display_name: 'Asia/Kamchatka', value: 'Asia/Kamchatka'},
    {display_name: 'Asia/Karachi', value: 'Asia/Karachi'},
    {display_name: 'Asia/Kathmandu', value: 'Asia/Kathmandu'},
    {display_name: 'Asia/Khandyga', value: 'Asia/Khandyga'},
    {display_name: 'Asia/Kolkata', value: 'Asia/Kolkata'},
    {display_name: 'Asia/Krasnoyarsk', value: 'Asia/Krasnoyarsk'},
    {display_name: 'Asia/Kuala_Lumpur', value: 'Asia/Kuala_Lumpur'},
    {display_name: 'Asia/Kuching', value: 'Asia/Kuching'},
    {display_name: 'Asia/Kuwait', value: 'Asia/Kuwait'},
    {display_name: 'Asia/Macau', value: 'Asia/Macau'},
    {display_name: 'Asia/Magadan', value: 'Asia/Magadan'},
    {display_name: 'Asia/Makassar', value: 'Asia/Makassar'},
    {display_name: 'Asia/Manila', value: 'Asia/Manila'},
    {display_name: 'Asia/Muscat', value: 'Asia/Muscat'},
    {display_name: 'Asia/Nicosia', value: 'Asia/Nicosia'},
    {display_name: 'Asia/Novokuznetsk', value: 'Asia/Novokuznetsk'},
    {display_name: 'Asia/Novosibirsk', value: 'Asia/Novosibirsk'},
    {display_name: 'Asia/Omsk', value: 'Asia/Omsk'},
    {display_name: 'Asia/Oral', value: 'Asia/Oral'},
    {display_name: 'Asia/Phnom_Penh', value: 'Asia/Phnom_Penh'},
    {display_name: 'Asia/Pontianak', value: 'Asia/Pontianak'},
    {display_name: 'Asia/Pyongyang', value: 'Asia/Pyongyang'},
    {display_name: 'Asia/Qatar', value: 'Asia/Qatar'},
    {display_name: 'Asia/Qostanay', value: 'Asia/Qostanay'},
    {display_name: 'Asia/Qyzylorda', value: 'Asia/Qyzylorda'},
    {display_name: 'Asia/Riyadh', value: 'Asia/Riyadh'},
    {display_name: 'Asia/Sakhalin', value: 'Asia/Sakhalin'},
    {display_name: 'Asia/Samarkand', value: 'Asia/Samarkand'},
    {display_name: 'Asia/Seoul', value: 'Asia/Seoul'},
    {display_name: 'Asia/Shanghai', value: 'Asia/Shanghai'},
    {display_name: 'Asia/Singapore', value: 'Asia/Singapore'},
    {display_name: 'Asia/Srednekolymsk', value: 'Asia/Srednekolymsk'},
    {display_name: 'Asia/Taipei', value: 'Asia/Taipei'},
    {display_name: 'Asia/Tashkent', value: 'Asia/Tashkent'},
    {display_name: 'Asia/Tbilisi', value: 'Asia/Tbilisi'},
    {display_name: 'Asia/Tehran', value: 'Asia/Tehran'},
    {display_name: 'Asia/Thimphu', value: 'Asia/Thimphu'},
    {display_name: 'Asia/Tokyo', value: 'Asia/Tokyo'},
    {display_name: 'Asia/Tomsk', value: 'Asia/Tomsk'},
    {display_name: 'Asia/Ulaanbaatar', value: 'Asia/Ulaanbaatar'},
    {display_name: 'Asia/Urumqi', value: 'Asia/Urumqi'},
    {display_name: 'Asia/Ust-Nera', value: 'Asia/Ust-Nera'},
    {display_name: 'Asia/Vientiane', value: 'Asia/Vientiane'},
    {display_name: 'Asia/Vladivostok', value: 'Asia/Vladivostok'},
    {display_name: 'Asia/Yakutsk', value: 'Asia/Yakutsk'},
    {display_name: 'Asia/Yangon', value: 'Asia/Yangon'},
    {display_name: 'Asia/Yekaterinburg', value: 'Asia/Yekaterinburg'},
    {display_name: 'Asia/Yerevan', value: 'Asia/Yerevan'},
    {display_name: 'Atlantic/Azores', value: 'Atlantic/Azores'},
    {display_name: 'Atlantic/Bermuda', value: 'Atlantic/Bermuda'},
    {display_name: 'Atlantic/Canary', value: 'Atlantic/Canary'},
    {display_name: 'Atlantic/Cape_Verde', value: 'Atlantic/Cape_Verde'},
    {display_name: 'Atlantic/Faroe', value: 'Atlantic/Faroe'},
    {display_name: 'Atlantic/Madeira', value: 'Atlantic/Madeira'},
    {display_name: 'Atlantic/Reykjavik', value: 'Atlantic/Reykjavik'},
    {display_name: 'Atlantic/South_Georgia', value: 'Atlantic/South_Georgia'},
    {display_name: 'Atlantic/St_Helena', value: 'Atlantic/St_Helena'},
    {display_name: 'Atlantic/Stanley', value: 'Atlantic/Stanley'},
    {display_name: 'Australia/Adelaide', value: 'Australia/Adelaide'},
    {display_name: 'Australia/Brisbane', value: 'Australia/Brisbane'},
    {display_name: 'Australia/Broken_Hill', value: 'Australia/Broken_Hill'},
    {display_name: 'Australia/Darwin', value: 'Australia/Darwin'},
    {display_name: 'Australia/Eucla', value: 'Australia/Eucla'},
    {display_name: 'Australia/Hobart', value: 'Australia/Hobart'},
    {display_name: 'Australia/Lindeman', value: 'Australia/Lindeman'},
    {display_name: 'Australia/Lord_Howe', value: 'Australia/Lord_Howe'},
    {display_name: 'Australia/Melbourne', value: 'Australia/Melbourne'},
    {display_name: 'Australia/Perth', value: 'Australia/Perth'},
    {display_name: 'Australia/Sydney', value: 'Australia/Sydney'},
    {display_name: 'Canada/Atlantic', value: 'Canada/Atlantic'},
    {display_name: 'Canada/Central', value: 'Canada/Central'},
    {display_name: 'Canada/Eastern', value: 'Canada/Eastern'},
    {display_name: 'Canada/Mountain', value: 'Canada/Mountain'},
    {display_name: 'Canada/Newfoundland', value: 'Canada/Newfoundland'},
    {display_name: 'Canada/Pacific', value: 'Canada/Pacific'},
    {display_name: 'Europe/Amsterdam', value: 'Europe/Amsterdam'},
    {display_name: 'Europe/Andorra', value: 'Europe/Andorra'},
    {display_name: 'Europe/Astrakhan', value: 'Europe/Astrakhan'},
    {display_name: 'Europe/Athens', value: 'Europe/Athens'},
    {display_name: 'Europe/Belgrade', value: 'Europe/Belgrade'},
    {display_name: 'Europe/Berlin', value: 'Europe/Berlin'},
    {display_name: 'Europe/Bratislava', value: 'Europe/Bratislava'},
    {display_name: 'Europe/Brussels', value: 'Europe/Brussels'},
    {display_name: 'Europe/Bucharest', value: 'Europe/Bucharest'},
    {display_name: 'Europe/Budapest', value: 'Europe/Budapest'},
    {display_name: 'Europe/Busingen', value: 'Europe/Busingen'},
    {display_name: 'Europe/Chisinau', value: 'Europe/Chisinau'},
    {display_name: 'Europe/Copenhagen', value: 'Europe/Copenhagen'},
    {display_name: 'Europe/Dublin', value: 'Europe/Dublin'},
    {display_name: 'Europe/Gibraltar', value: 'Europe/Gibraltar'},
    {display_name: 'Europe/Guernsey', value: 'Europe/Guernsey'},
    {display_name: 'Europe/Helsinki', value: 'Europe/Helsinki'},
    {display_name: 'Europe/Isle_of_Man', value: 'Europe/Isle_of_Man'},
    {display_name: 'Europe/Istanbul', value: 'Europe/Istanbul'},
    {display_name: 'Europe/Jersey', value: 'Europe/Jersey'},
    {display_name: 'Europe/Kaliningrad', value: 'Europe/Kaliningrad'},
    {display_name: 'Europe/Kirov', value: 'Europe/Kirov'},
    {display_name: 'Europe/Kyiv', value: 'Europe/Kyiv'},
    {display_name: 'Europe/Lisbon', value: 'Europe/Lisbon'},
    {display_name: 'Europe/Ljubljana', value: 'Europe/Ljubljana'},
    {display_name: 'Europe/London', value: 'Europe/London'},
    {display_name: 'Europe/Luxembourg', value: 'Europe/Luxembourg'},
    {display_name: 'Europe/Madrid', value: 'Europe/Madrid'},
    {display_name: 'Europe/Malta', value: 'Europe/Malta'},
    {display_name: 'Europe/Mariehamn', value: 'Europe/Mariehamn'},
    {display_name: 'Europe/Minsk', value: 'Europe/Minsk'},
    {display_name: 'Europe/Monaco', value: 'Europe/Monaco'},
    {display_name: 'Europe/Moscow', value: 'Europe/Moscow'},
    {display_name: 'Europe/Oslo', value: 'Europe/Oslo'},
    {display_name: 'Europe/Paris', value: 'Europe/Paris'},
    {display_name: 'Europe/Podgorica', value: 'Europe/Podgorica'},
    {display_name: 'Europe/Prague', value: 'Europe/Prague'},
    {display_name: 'Europe/Riga', value: 'Europe/Riga'},
    {display_name: 'Europe/Rome', value: 'Europe/Rome'},
    {display_name: 'Europe/Samara', value: 'Europe/Samara'},
    {display_name: 'Europe/San_Marino', value: 'Europe/San_Marino'},
    {display_name: 'Europe/Sarajevo', value: 'Europe/Sarajevo'},
    {display_name: 'Europe/Saratov', value: 'Europe/Saratov'},
    {display_name: 'Europe/Simferopol', value: 'Europe/Simferopol'},
    {display_name: 'Europe/Skopje', value: 'Europe/Skopje'},
    {display_name: 'Europe/Sofia', value: 'Europe/Sofia'},
    {display_name: 'Europe/Stockholm', value: 'Europe/Stockholm'},
    {display_name: 'Europe/Tallinn', value: 'Europe/Tallinn'},
    {display_name: 'Europe/Tirane', value: 'Europe/Tirane'},
    {display_name: 'Europe/Ulyanovsk', value: 'Europe/Ulyanovsk'},
    {display_name: 'Europe/Uzhgorod', value: 'Europe/Uzhgorod'},
    {display_name: 'Europe/Vaduz', value: 'Europe/Vaduz'},
    {display_name: 'Europe/Vatican', value: 'Europe/Vatican'},
    {display_name: 'Europe/Vienna', value: 'Europe/Vienna'},
    {display_name: 'Europe/Vilnius', value: 'Europe/Vilnius'},
    {display_name: 'Europe/Volgograd', value: 'Europe/Volgograd'},
    {display_name: 'Europe/Warsaw', value: 'Europe/Warsaw'},
    {display_name: 'Europe/Zagreb', value: 'Europe/Zagreb'},
    {display_name: 'Europe/Zaporozhye', value: 'Europe/Zaporozhye'},
    {display_name: 'Europe/Zurich', value: 'Europe/Zurich'},
    {display_name: 'GMT', value: 'GMT'},
    {display_name: 'Indian/Antananarivo', value: 'Indian/Antananarivo'},
    {display_name: 'Indian/Chagos', value: 'Indian/Chagos'},
    {display_name: 'Indian/Christmas', value: 'Indian/Christmas'},
    {display_name: 'Indian/Cocos', value: 'Indian/Cocos'},
    {display_name: 'Indian/Comoro', value: 'Indian/Comoro'},
    {display_name: 'Indian/Kerguelen', value: 'Indian/Kerguelen'},
    {display_name: 'Indian/Mahe', value: 'Indian/Mahe'},
    {display_name: 'Indian/Maldives', value: 'Indian/Maldives'},
    {display_name: 'Indian/Mauritius', value: 'Indian/Mauritius'},
    {display_name: 'Indian/Mayotte', value: 'Indian/Mayotte'},
    {display_name: 'Indian/Reunion', value: 'Indian/Reunion'},
    {display_name: 'Pacific/Apia', value: 'Pacific/Apia'},
    {display_name: 'Pacific/Auckland', value: 'Pacific/Auckland'},
    {display_name: 'Pacific/Bougainville', value: 'Pacific/Bougainville'},
    {display_name: 'Pacific/Chatham', value: 'Pacific/Chatham'},
    {display_name: 'Pacific/Chuuk', value: 'Pacific/Chuuk'},
    {display_name: 'Pacific/Easter', value: 'Pacific/Easter'},
    {display_name: 'Pacific/Efate', value: 'Pacific/Efate'},
    {display_name: 'Pacific/Fakaofo', value: 'Pacific/Fakaofo'},
    {display_name: 'Pacific/Fiji', value: 'Pacific/Fiji'},
    {display_name: 'Pacific/Funafuti', value: 'Pacific/Funafuti'},
    {display_name: 'Pacific/Galapagos', value: 'Pacific/Galapagos'},
    {display_name: 'Pacific/Gambier', value: 'Pacific/Gambier'},
    {display_name: 'Pacific/Guadalcanal', value: 'Pacific/Guadalcanal'},
    {display_name: 'Pacific/Guam', value: 'Pacific/Guam'},
    {display_name: 'Pacific/Honolulu', value: 'Pacific/Honolulu'},
    {display_name: 'Pacific/Kanton', value: 'Pacific/Kanton'},
    {display_name: 'Pacific/Kiritimati', value: 'Pacific/Kiritimati'},
    {display_name: 'Pacific/Kosrae', value: 'Pacific/Kosrae'},
    {display_name: 'Pacific/Kwajalein', value: 'Pacific/Kwajalein'},
    {display_name: 'Pacific/Majuro', value: 'Pacific/Majuro'},
    {display_name: 'Pacific/Marquesas', value: 'Pacific/Marquesas'},
    {display_name: 'Pacific/Midway', value: 'Pacific/Midway'},
    {display_name: 'Pacific/Nauru', value: 'Pacific/Nauru'},
    {display_name: 'Pacific/Niue', value: 'Pacific/Niue'},
    {display_name: 'Pacific/Norfolk', value: 'Pacific/Norfolk'},
    {display_name: 'Pacific/Noumea', value: 'Pacific/Noumea'},
    {display_name: 'Pacific/Pago_Pago', value: 'Pacific/Pago_Pago'},
    {display_name: 'Pacific/Palau', value: 'Pacific/Palau'},
    {display_name: 'Pacific/Pitcairn', value: 'Pacific/Pitcairn'},
    {display_name: 'Pacific/Pohnpei', value: 'Pacific/Pohnpei'},
    {display_name: 'Pacific/Port_Moresby', value: 'Pacific/Port_Moresby'},
    {display_name: 'Pacific/Rarotonga', value: 'Pacific/Rarotonga'},
    {display_name: 'Pacific/Saipan', value: 'Pacific/Saipan'},
    {display_name: 'Pacific/Tahiti', value: 'Pacific/Tahiti'},
    {display_name: 'Pacific/Tarawa', value: 'Pacific/Tarawa'},
    {display_name: 'Pacific/Tongatapu', value: 'Pacific/Tongatapu'},
    {display_name: 'Pacific/Wake', value: 'Pacific/Wake'},
    {display_name: 'Pacific/Wallis', value: 'Pacific/Wallis'},
    {display_name: 'US/Alaska', value: 'US/Alaska'},
    {display_name: 'US/Arizona', value: 'US/Arizona'},
    {display_name: 'US/Central', value: 'US/Central'},
    {display_name: 'US/Eastern', value: 'US/Eastern'},
    {display_name: 'US/Hawaii', value: 'US/Hawaii'},
    {display_name: 'US/Mountain', value: 'US/Mountain'},
    {display_name: 'US/Pacific', value: 'US/Pacific'},
    {display_name: 'UTC', value: 'UTC'}
]

const HISTORY_INTERVAL_CHOICES = [
    {display_name: gettext('disabled'), value: 0},
    {display_name: gettext('when value changes'), value: -1},
    {display_name: gettext('1 second'), value: 1},
    {display_name: StringUtils.formatPercent(gettext('%(count)d seconds'), {count: 5}), value: 5},
    {display_name: StringUtils.formatPercent(gettext('%(count)d seconds'), {count: 10}), value: 10},
    {display_name: StringUtils.formatPercent(gettext('%(count)d seconds'), {count: 30}), value: 30},
    {display_name: gettext('1 minute'), value: 60},
    {display_name: StringUtils.formatPercent(gettext('%(count)d minutes'), {count: 5}), value: 300},
    {display_name: StringUtils.formatPercent(gettext('%(count)d minutes'), {count: 10}), value: 600},
    {display_name: StringUtils.formatPercent(gettext('%(count)d minutes'), {count: 15}), value: 900},
    {display_name: StringUtils.formatPercent(gettext('%(count)d minutes'), {count: 30}), value: 1800},
    {display_name: gettext('1 hour'), value: 3600},
    {display_name: StringUtils.formatPercent(gettext('%(count)d hours'), {count: 4}), value: 14400},
    {display_name: StringUtils.formatPercent(gettext('%(count)d hours'), {count: 8}), value: 28800},
    {display_name: StringUtils.formatPercent(gettext('%(count)d hours'), {count: 12}), value: 43200},
    {display_name: gettext('1 day'), value: 86400}
]

const HISTORY_RETENTION_CHOICES = [
    {display_name: gettext('forever'), value: 0},
    {display_name: gettext('1 minute'), value: 60},
    {display_name: gettext('1 hour'), value: 3600},
    {display_name: gettext('1 day'), value: 86400},
    {display_name: gettext('1 week'), value: 86400 * 7},
    {display_name: gettext('1 month'), value: 86400 * 31},
    {display_name: gettext('1 year'), value: 86400 * 366}
]


/**
 * @alias qtoggle.api.attrdefs.STD_DEVICE_ATTRDEFS
 * @type {Object}
 */
export const STD_DEVICE_ATTRDEFS = {
    name: {
        display_name: gettext('Device Name'),
        description: gettext('A unique name given to the device (usually its hostname).'),
        type: 'string',
        max: 32,
        required: true,
        modifiable: true,
        standard: true,
        separator: true,
        order: 100,
        field: {
            class: TextField,
            maxLength: 32,
            pattern: /^[_a-zA-Z][_a-zA-Z0-9-]*$/
        }
    },
    display_name: {
        display_name: gettext('Display Name'),
        description: gettext('A friendly name to be used when showing the device.'),
        type: 'string',
        max: 64,
        modifiable: true,
        standard: true,
        order: 110
    },
    version: {
        display_name: gettext('Firmware Version'),
        type: 'string',
        modifiable: false,
        standard: true,
        order: 120
    },
    api_version: {
        display_name: gettext('API Version'),
        description: gettext('The qToggle API version implemented and supported by the device.'),
        type: 'string',
        modifiable: false,
        standard: true,
        order: 130
    },
    vendor: {
        display_name: gettext('Vendor'),
        type: 'string',
        modifiable: false,
        standard: true,
        order: 140
    },
    admin_password: {
        display_name: gettext('Administrator Password'),
        description: gettext("The administrator's password, required to perform administrative tasks."),
        type: 'string',
        max: 32,
        modifiable: true,
        standard: true,
        showAnyway: true,
        separator: true,
        order: 150,
        field: {
            class: PasswordField,
            clearEnabled: true,
            clearPlaceholder: true,
            maxLength: 32,
            placeholder: `(${gettext('unset')})`
        },
        checkWarning: v => v ? null : gettext('Please set a password. Leaving this password empty is extremely unsafe!')
    },
    normal_password: {
        display_name: gettext('Normal Password'),
        description: gettext("The normal user's password, required to perform regular tasks."),
        type: 'string',
        max: 32,
        optional: true,
        modifiable: true,
        standard: true,
        showAnyway: true,
        order: 151,
        field: {
            class: PasswordField,
            clearEnabled: true,
            clearPlaceholder: true,
            maxLength: 32,
            placeholder: `(${gettext('unset')})`
        },
        checkWarning: v => v ? null : gettext('Please set a password. Leaving this password empty is extremely unsafe!')
    },
    viewonly_password: {
        display_name: gettext('View-only Password'),
        description: gettext("The view-only user's password required for view-only privileges."),
        type: 'string',
        max: 32,
        optional: true,
        modifiable: true,
        standard: true,
        showAnyway: true,
        order: 152,
        field: {
            class: PasswordField,
            clearEnabled: true,
            clearPlaceholder: true,
            maxLength: 32,
            placeholder: `(${gettext('unset')})`
        },
        checkWarning: v => v ? null : gettext('Please set a password. Leaving this password empty is extremely unsafe!')
    },
    date: {
        display_name: gettext('System Date/Time'),
        description: gettext("The current system date and time, in your app's timezone."),
        type: 'string',
        modifiable: true,
        optional: true,
        standard: true,
        separator: true,
        order: 160,
        valueToUI: v => DateUtils.formatPercent(new Date(v * 1000), '%Y-%m-%d %H:%M:%S'),
        valueFromUI: v => Math.round(Date.parse(v) / 1000),
        field: {
            class: TextField,
            pattern: DATE_PATTERN
        }
    },
    timezone: {
        display_name: gettext('Timezone'),
        type: 'string',
        choices: TIMEZONE_CHOICES,
        modifiable: true,
        optional: true,
        standard: true,
        separator: false,
        order: 161
    },
    uptime: {
        display_name: gettext('Uptime'),
        description: gettext('The number of seconds passed since the device has been turned on.'),
        type: 'number',
        unit: gettext('s'),
        integer: true,
        modifiable: false,
        optional: true,
        standard: true,
        order: 162
    },
    wifi_ssid: {
        display_name: gettext('Wi-Fi Network'),
        description: gettext('Your Wi-Fi network name. Leave empty when not using Wi-Fi.'),
        separator: true,
        type: 'string',
        modifiable: true,
        reconnect: true,
        max: 32,
        optional: true,
        standard: true,
        order: 170
    },
    wifi_key: {
        display_name: gettext('Wi-Fi Key'),
        description: gettext('Your Wi-Fi network key (password). Leave empty for an open Wi-Fi network.'),
        type: 'string',
        modifiable: true,
        reconnect: true,
        max: 64,
        optional: true,
        standard: true,
        order: 171,
        field: {
            class: PasswordField,
            clearEnabled: true,
            revealOnFocus: true,
            maxLength: 64
        }
    },
    wifi_bssid: {
        display_name: gettext('Wi-Fi BSSID'),
        description: gettext('A specific BSSID (MAC address) of a Wi-Fi access point. ' +
                             'Leave empty for automatic selection.'),
        type: 'string',
        modifiable: true,
        reconnect: true,
        optional: true,
        standard: true,
        order: 172,
        field: {
            class: TextField,
            clearEnabled: true,
            placeholder: 'AA:BB:CC:DD:EE:FF',
            pattern: /^[a-fA-F0-9]{2}:[a-fA-F0-9]{2}:[a-fA-F0-9]{2}:[a-fA-F0-9]{2}:[a-fA-F0-9]{2}:[a-fA-F0-9]{2}$/
        }
    },
    wifi_bssid_current: {
        display_name: gettext('Wi-Fi BSSID (Current)'),
        description: gettext('The BSSID (MAC address) of the access point to which the device is currently connected.'),
        type: 'string',
        modifiable: false,
        optional: true,
        standard: true,
        order: 173
    },
    wifi_signal_strength: {
        display_name: gettext('Wi-Fi Strength'),
        description: gettext('Indicates the quality of the Wi-Fi connection.'),
        type: 'number',
        modifiable: false,
        optional: true,
        standard: true,
        order: 174,
        field: {
            class: WiFiSignalStrengthField
        }
    },
    ip_address: {
        display_name: gettext('IP Address'),
        description: gettext('Manually configured IP address. Leave empty for automatic (DHCP) configuration.'),
        separator: true,
        type: 'string',
        modifiable: true,
        reconnect: true,
        optional: true,
        standard: true,
        order: 180,
        field: {
            class: TextField,
            placeholder: '192.168.1.2',
            pattern: IP_ADDRESS_PATTERN
        }
    },
    ip_netmask: {
        display_name: gettext('Network Mask'),
        description: gettext('Manually configured network mask. Leave empty for automatic (DHCP) configuration.'),
        type: 'number',
        modifiable: true,
        integer: true,
        reconnect: true,
        optional: true,
        standard: true,
        order: 181,
        valueToUI: v => v ? netmaskFromLen(v) : '',
        valueFromUI: v => v ? netmaskToLen(v) : 0,
        field: {
            class: TextField,
            placeholder: '255.255.255.0',
            pattern: IP_ADDRESS_PATTERN
        }
    },
    ip_gateway: {
        display_name: gettext('Gateway'),
        description: gettext('Manually configured gateway (default route). ' +
                             'Leave empty for automatic (DHCP) configuration.'),
        type: 'string',
        modifiable: true,
        reconnect: true,
        optional: true,
        standard: true,
        order: 182,
        field: {
            class: TextField,
            placeholder: '192.168.1.1',
            pattern: IP_ADDRESS_PATTERN
        }
    },
    ip_dns: {
        display_name: gettext('DNS Server'),
        description: gettext('Manually configured DNS server. Leave empty for automatic (DHCP) configuration.'),
        type: 'string',
        modifiable: true,
        reconnect: true,
        optional: true,
        standard: true,
        order: 183,
        field: {
            class: TextField,
            placeholder: '192.168.1.1',
            pattern: IP_ADDRESS_PATTERN
        }
    },
    ip_address_current: {
        display_name: gettext('IP Address (Current)'),
        type: 'string',
        modifiable: false,
        optional: true,
        standard: true,
        order: 184
    },
    ip_netmask_current: {
        display_name: gettext('Network Mask (Current)'),
        type: 'number',
        modifiable: false,
        optional: true,
        standard: true,
        valueToUI: v => v ? netmaskFromLen(v) : '',
        field: {
            class: TextField
        },
        order: 185
    },
    ip_gateway_current: {
        display_name: gettext('Gateway (Current)'),
        type: 'string',
        modifiable: false,
        optional: true,
        standard: true,
        order: 186
    },
    ip_dns_current: {
        display_name: gettext('DNS Server (Current)'),
        type: 'string',
        modifiable: false,
        optional: true,
        standard: true,
        order: 187
    },
    cpu_usage: {
        display_name: gettext('CPU Usage'),
        unit: '%',
        type: 'number',
        modifiable: false,
        optional: true,
        standard: true,
        order: 190,
        field: {
            class: ProgressDiskField,
            color: '@red-color'
        }
    },
    mem_usage: {
        display_name: gettext('Memory Usage'),
        unit: '%',
        type: 'number',
        modifiable: false,
        optional: true,
        standard: true,
        order: 191,
        field: {
            class: ProgressDiskField,
            color: '@green-color'
        }
    },
    storage_usage: {
        display_name: gettext('Storage Usage'),
        unit: '%',
        type: 'number',
        modifiable: false,
        optional: true,
        standard: true,
        order: 192,
        field: {
            class: ProgressDiskField,
            color: '@blue-color'
        }
    },
    temperature: {
        display_name: gettext('Temperature'),
        unit: '\xb0C',
        type: 'number',
        modifiable: false,
        optional: true,
        standard: true,
        order: 193,
        field: function (def) {
            if (def.min != null && def.max != null) {
                return {
                    class: ProgressDiskField,
                    color: '@magenta-color',
                    caption: '%s&deg;C'
                }
            }
            else {
                return {
                    class: TextField
                }
            }
        }
    },
    battery_level: {
        display_name: gettext('Battery Level'),
        unit: '%',
        type: 'number',
        modifiable: false,
        optional: true,
        standard: true,
        order: 194,
        field: {
            class: ProgressDiskField,
            color: '@orange-color'
        }
    },
    low_battery: {
        display_name: gettext('Low Battery'),
        type: 'boolean',
        modifiable: false,
        optional: true,
        standard: true,
        order: 195
    },
    flags: {
        display_name: gettext('Device Features'),
        description: gettext('Device flags that indicate support for various optional functions.'),
        separator: true,
        type: 'flags', // TODO replace with list of strings
        standard: true,
        order: 200
    },
    config_name: {
        display_name: gettext('Configuration Name'),
        description: gettext('Indicates a particular device configuration.'),
        type: 'string',
        modifiable: true,
        optional: true,
        standard: true,
        order: 210,
        field: {
            class: ConfigNameField
        }
    },
    virtual_ports: {
        display_name: gettext('Virtual Ports'),
        description: gettext('Indicates the maximum number of virtual ports supported by the device.'),
        type: 'number',
        integer: 'true',
        modifiable: false,
        optional: true,
        standard: true,
        order: 220
    }
}

/**
 * @alias qtoggle.api.attrdefs.ADDITIONAL_DEVICE_ATTRDEFS
 * @type {Object}
 */
export const ADDITIONAL_DEVICE_ATTRDEFS = {
}

/**
 * @alias qtoggle.api.attrdefs.STD_PORT_ATTRDEFS
 * @type {Object}
 */
export const STD_PORT_ATTRDEFS = {
    id: {
        display_name: gettext('Port Identifier'),
        description: gettext('The unique identifier of the port.'),
        type: 'string',
        max: 64,
        modifiable: false,
        standard: true,
        order: 100,
        field: {
            class: TextField,
            maxLength: 64,
            pattern: /^[_a-zA-Z][._a-zA-Z0-9-]*$/
        }
    },
    enabled: {
        display_name: gettext('Enabled'),
        type: 'boolean',
        modifiable: true,
        standard: true,
        order: 110
    },
    online: {
        display_name: gettext('Online'),
        type: 'boolean',
        modifiable: false,
        standard: true,
        optional: true,
        order: 120
    },
    last_sync: {
        display_name: gettext('Last Sync'),
        description: gettext('The last time when the value of this port has been updated.'),
        type: 'string',
        modifiable: false,
        standard: true,
        valueToUI: function (value) {
            if (value == null || value < 0) {
                return `(${gettext('never')})`
            }
            else {
                return DateUtils.formatPercent(new Date(value * 1000), '%Y-%m-%d %H:%M:%S')
            }
        },
        order: 130
    },
    expires: {
        display_name: gettext('Expires'),
        description: gettext('The number of seconds before the port value is considered expired. 0 means ' +
                             'that port value never expires.'),
        unit: gettext('s'),
        type: 'number',
        modifiable: true,
        standard: true,
        min: 0,
        max: 2147483647,
        integer: true,
        order: 140
    },
    type: {
        display_name: gettext('Type'),
        description: gettext('The data type of the port value.'),
        type: 'string',
        choices: [
            {display_name: gettext('Boolean'), value: 'boolean'},
            {display_name: gettext('Number'), value: 'number'}
        ],
        modifiable: false,
        separator: true,
        standard: true,
        order: 150
    },
    display_name: {
        display_name: gettext('Display Name'),
        description: gettext('A friendly name to be used when showing the port.'),
        type: 'string',
        max: 64,
        modifiable: true,
        standard: true,
        order: 160
    },
    unit: {
        display_name: gettext('Unit'),
        description: gettext('The unit of measurement for the value of this port.'),
        type: 'string',
        max: 64,
        modifiable: true,
        standard: true,
        optional: true,
        order: 170
    },
    writable: {
        display_name: gettext('Writable'),
        description: gettext('Tells if values can be written to the port.'),
        type: 'boolean',
        modifiable: false,
        standard: true,
        order: 180
    },
    persisted: {
        display_name: gettext('Persist Value'),
        description: gettext('Controls whether the port value is preserved and restored when device is restarted.'),
        type: 'boolean',
        modifiable: true,
        standard: true,
        optional: true,
        order: 181
    },
    internal: {
        display_name: gettext('Internal'),
        description: gettext("Indicates that the port's usage is limited to the device internal scope and has no " +
                             'meaning outside of it.'),
        type: 'boolean',
        modifiable: true,
        standard: true,
        optional: true,
        order: 182
    },
    min: {
        display_name: gettext('Minimum Value'),
        description: gettext('The minimum accepted value for this port.'),
        type: 'number',
        modifiable: false,
        separator: true,
        standard: true,
        optional: true,
        order: 190
    },
    max: {
        display_name: gettext('Maximum Value'),
        description: gettext('The maximum accepted value for this port.'),
        type: 'number',
        modifiable: false,
        standard: true,
        optional: true,
        order: 200
    },
    integer: {
        display_name: gettext('Integer Values'),
        description: gettext('Indicates that only integer values are accepted for this port.'),
        type: 'boolean',
        modifiable: false,
        standard: true,
        optional: true,
        order: 210
    },
    step: {
        display_name: gettext('Step'),
        description: gettext("Indicates the granularity for this port's value."),
        type: 'number',
        modifiable: false,
        standard: true,
        optional: true,
        order: 220
    },
    // TODO choices
    tag: {
        display_name: gettext('Tag'),
        description: gettext('User-defined details.'),
        type: 'string',
        max: 64,
        modifiable: true,
        separator: true,
        standard: true,
        optional: true,
        order: 230
    },
    virtual: {
        display_name: gettext('Virtual Port'),
        description: gettext('Tells whether this is a virtual port or not.'),
        type: 'boolean',
        modifiable: false,
        standard: true,
        optional: true,
        order: 240
    },
    expression: {
        display_name: gettext('Expression'),
        description: gettext('An expression that controls the port value.'),
        type: 'string',
        modifiable: true,
        separator: true,
        standard: true,
        optional: true,
        order: 250,
        field: {
            class: TextAreaField,
            resize: 'vertical'
        }
    },
    device_expression: {
        /* display_name is added dynamically */
        description: gettext('An expression that controls the port value directly on the device.'),
        type: 'string',
        modifiable: true,
        standard: true,
        optional: true,
        field: {
            class: TextAreaField,
            resize: 'vertical'
        }
        /* order is added dynamically */
    },
    transform_write: {
        display_name: gettext('Write Transform Expression'),
        description: gettext('An expression to be applied on the value when written to the port.'),
        type: 'string',
        modifiable: true,
        standard: true,
        optional: true,
        order: 260
    },
    transform_read: {
        display_name: gettext('Read Transform Expression'),
        description: gettext('An expression to be applied on the value read from the port.'),
        type: 'string',
        modifiable: true,
        standard: true,
        optional: true,
        order: 270
    },
    history_interval: {
        display_name: gettext('History Sampling Interval'),
        description: gettext('Determines how often the port value will be sampled and saved to history.'),
        type: 'number',
        choices: HISTORY_INTERVAL_CHOICES,
        modifiable: true,
        standard: true,
        optional: true,
        separator: true,
        order: 280
    },
    device_history_interval: {
        /* display_name is added dynamically */
        description: gettext(
            'Determines how often the port value will be sampled and saved to history, directly on the device.'
        ),
        type: 'number',
        choices: HISTORY_INTERVAL_CHOICES,
        modifiable: true,
        standard: true,
        optional: true,
        separator: true
        /* order is added dynamically */
    },
    history_retention: {
        display_name: gettext('History Retention Duration'),
        description: gettext('Determines for how long historical data will be kept for this port.'),
        type: 'number',
        choices: HISTORY_RETENTION_CHOICES,
        modifiable: true,
        standard: true,
        optional: true,
        order: 290
    },
    device_history_retention: {
        /* display_name is added dynamically */
        description: gettext(
            'Determines for how long historical data will be kept for this port, directly on the device.'
        ),
        type: 'number',
        choices: HISTORY_RETENTION_CHOICES,
        modifiable: true,
        standard: true,
        optional: true
        /* order is added dynamically */
    }
}

/**
 * @alias qtoggle.api.attrdefs.ADDITIONAL_PORT_ATTRDEFS
 * @type {Object}
 */
export const ADDITIONAL_PORT_ATTRDEFS = {
}

/* All standard and known additional attribute definitions have the "known" field set to true */
ObjectUtils.forEach(STD_DEVICE_ATTRDEFS, (name, def) => {
    def.known = true
})
ObjectUtils.forEach(ADDITIONAL_DEVICE_ATTRDEFS, (name, def) => {
    def.known = true
})
ObjectUtils.forEach(STD_PORT_ATTRDEFS, (name, def) => {
    def.known = true
})
ObjectUtils.forEach(ADDITIONAL_PORT_ATTRDEFS, (name, def) => {
    def.known = true
})


/**
 * Combine two sets of attribute definitions.
 * @alias qtoggle.api.attrdefs.combineAttrdefs
 * @param {Object} defs1
 * @param {Object} defs2
 * @returns {Object}
 */
export function combineAttrdefs(defs1, defs2) {
    let combined = ObjectUtils.copy(defs1, /* deep = */ true)

    ObjectUtils.forEach(defs2, function (name, def) {
        combined[name] = ObjectUtils.combine(combined[name] || {}, def)
    })

    return combined
}
