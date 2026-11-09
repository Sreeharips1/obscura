const ICONS = {
  phone: <path d="M5 4h4l2 5-2.5 1.5a11 11 0 005 5L15 13l5 2v4a2 2 0 01-2 2A16 16 0 013 6a2 2 0 012-2z" />,
  mail: (
    <>
      <rect x="3" y="5" width="18" height="14" rx="2" />
      <path d="M3 7l9 6 9-6" />
    </>
  ),
  user: (
    <>
      <circle cx="12" cy="8" r="4" />
      <path d="M4 21a8 8 0 0116 0" />
    </>
  ),
  idcard: (
    <>
      <rect x="3" y="5" width="18" height="14" rx="2" />
      <circle cx="9" cy="11" r="2" />
      <path d="M6 16c.6-1.6 2-2.4 3-2.4s2.4.8 3 2.4M14 10h4M14 14h4" />
    </>
  ),
  card: (
    <>
      <rect x="2.5" y="5" width="19" height="14" rx="2" />
      <path d="M2.5 10h19M6 15h4" />
    </>
  ),
  bank: <path d="M3 10l9-6 9 6M5 10v8M9.5 10v8M14.5 10v8M19 10v8M3 20h18" />,
  key: (
    <>
      <circle cx="8" cy="15" r="4" />
      <path d="M11 12l9-9M16 7l3 3" />
    </>
  ),
  lock: (
    <>
      <rect x="5" y="11" width="14" height="10" rx="2" />
      <path d="M8 11V8a4 4 0 018 0v3" />
    </>
  ),
  link: <path d="M10 14a4 4 0 005.7 0l3-3a4 4 0 00-5.7-5.7l-1 1M14 10a4 4 0 00-5.7 0l-3 3A4 4 0 0011 18.7l1-1" />,
  globe: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M3 12h18M12 3a14 14 0 010 18M12 3a14 14 0 000 18" />
    </>
  ),
  device: (
    <>
      <rect x="7" y="2.5" width="10" height="19" rx="2" />
      <path d="M11 18.5h2" />
    </>
  ),
  pin: (
    <>
      <path d="M12 21s7-6.2 7-11a7 7 0 10-14 0c0 4.8 7 11 7 11z" />
      <circle cx="12" cy="10" r="2.5" />
    </>
  ),
  building: <path d="M4 21V5a1 1 0 011-1h8a1 1 0 011 1v16M14 10h5a1 1 0 011 1v10M3 21h18M8 8h2M8 12h2M8 16h2" />,
  briefcase: (
    <>
      <rect x="3" y="7" width="18" height="13" rx="2" />
      <path d="M9 7V5a1 1 0 011-1h4a1 1 0 011 1v2M3 13h18" />
    </>
  ),
  folder: <path d="M3 7a2 2 0 012-2h4l2 2h8a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2z" />,
  shield: (
    <>
      <path d="M12 3l8 3v6c0 4.5-3.2 8-8 9-4.8-1-8-4.5-8-9V6z" />
      <path d="M12 8v4M12 15.5v.01" />
    </>
  ),
  qr: (
    <>
      <rect x="3" y="3" width="7" height="7" rx="1" />
      <rect x="14" y="3" width="7" height="7" rx="1" />
      <rect x="3" y="14" width="7" height="7" rx="1" />
      <path d="M14 14h3v3M21 14v.01M14 21h3M21 17v4" />
    </>
  ),
  barcode: <path d="M4 5v14M7 5v14M11 5v14M14 5v14M18 5v14M20 5v14" />,
  face: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M9 10h.01M15 10h.01M8.5 14.5a4.5 4.5 0 007 0" />
    </>
  ),
  car: <path d="M3 15v-3l2-5h14l2 5v3zM6 18v-3M18 18v-3M5 12h14" />,
  monitor: (
    <>
      <rect x="3" y="4" width="18" height="12" rx="2" />
      <path d="M8 20h8M12 16v4" />
    </>
  ),
  calendar: (
    <>
      <rect x="4" y="5" width="16" height="16" rx="2" />
      <path d="M4 10h16M8 3v4M16 3v4" />
    </>
  ),
  info: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 11v5M12 8v.01" />
    </>
  ),
};

function Svg({ name, size = 16 }) {
  return (
    <svg
      viewBox="0 0 24 24"
      width={size}
      height={size}
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {ICONS[name] || ICONS.shield}
    </svg>
  );
}

// type: [icon, group, title, why it is risky]
const INFO = {
  EMAIL: ["mail", "contact", "Email address", "It points straight to you. It is used for spam and phishing, and it links your messages to your accounts and identity."],
  PHONE: ["phone", "contact", "Phone number", "It identifies you directly and is used for scam calls, SIM-swap fraud and tracking. It is often tied to your bank and one-time codes."],
  AADHAAR_LIKE: ["idcard", "id", "Aadhaar-style ID number", "A national ID number. With a name it enables identity theft and fake KYC, and a leaked ID number cannot be changed."],
  PAN_LIKE: ["idcard", "id", "PAN-style tax ID", "A tax ID linked to your finances. Combined with other details it enables identity fraud and fake loan or account applications."],
  NATIONAL_ID: ["idcard", "id", "National ID", "A government ID number. It is used for identity theft and cannot easily be replaced once leaked."],
  PASSPORT_NUMBER: ["idcard", "id", "Passport number", "A passport number can be used for identity fraud and fake travel or account applications."],
  DRIVER_LICENSE: ["idcard", "id", "Driver licence number", "A licence number identifies you officially and is used for identity fraud."],
  IFSC_CODE: ["bank", "finance", "Bank branch code", "Low risk alone, but together with an account number it points to your bank account."],
  BANK_ACCOUNT: ["bank", "finance", "Bank account number", "Can be used for unauthorised debits, fraud and social-engineering calls pretending to be your bank."],
  UPI_ID: ["bank", "finance", "UPI ID", "Anyone with your UPI ID can send payment requests in your name, which helps payment scams."],
  CARD_NUMBER_LIKE: ["card", "finance", "Payment card number", "Card numbers can be used for fraudulent payments. Payment details should never be shared with an outside service."],
  IP_ADDRESS: ["globe", "device", "IP address", "Reveals your rough location and network, and can be used to track or target a device."],
  MAC_ADDRESS: ["device", "device", "Device MAC address", "A hardware ID for your device. It can follow one device across networks and be used to fingerprint it."],
  IMEI: ["device", "device", "Phone IMEI number", "A unique number for a phone handset. It identifies the device and is used in theft and cloning scams."],
  SENSITIVE_URL: ["link", "secret", "Link with a token", "This link seems to contain a token or key. Anyone who has it may be able to log in or see your data."],
  PERSON_NAME: ["user", "identity", "Person name", "A name ties the rest of your text to a real person. Together with other details it makes you identifiable."],
  USERNAME: ["user", "identity", "Username", "A username identifies an account and can be searched across websites to find you."],
  ADDRESS: ["pin", "location", "Address", "A home address shows where you live, which makes stalking, burglary and fraud easier."],
  LOCATION: ["pin", "location", "Location", "Places you live or visit reveal your routine and narrow down who you are."],
  FACILITY: ["pin", "location", "Named place", "Places such as your office or school reveal where you spend your time."],
  ORGANIZATION: ["building", "work", "Organization", "Your workplace or school helps identify you and may reveal confidential business relationships."],
  EMPLOYER: ["briefcase", "work", "Employer", "Your employer, together with your name, makes you easy to find and can expose company information."],
  PROJECT_NAME: ["folder", "work", "Project name", "Internal project names can expose unreleased or confidential work."],
  CONFIDENTIAL_CONTEXT: ["lock", "work", "Confidential wording", "The wording suggests this content is meant to stay private, such as internal or secret material."],
  DATE: ["calendar", "identity", "Date", "Dates such as birthdays are used to confirm identity and to answer security questions."],
  PASSWORD: ["key", "secret", "Password", "A password gives full access to an account. It is never sent to the AI."],
  API_KEY_OR_TOKEN: ["key", "secret", "API key or token", "Keys and tokens work like passwords. Anyone who sees one can use your services and run up costs. It is never sent."],
  JWT_TOKEN: ["key", "secret", "Login token", "Whoever holds this token can act as you until it expires. It is never sent."],
  PRIVATE_KEY: ["lock", "secret", "Private key", "A private key proves your identity to servers. If it leaks it must be replaced. It is never sent."],
  QR_CODE: ["qr", "visual", "QR code", "A QR code can hide a link, a payment request or a login. Scanning it can expose your account or data."],
  BARCODE: ["barcode", "visual", "Barcode", "Barcodes can encode tickets, IDs or account numbers that anyone can scan."],
  FACE: ["face", "visual", "Face", "A face identifies you and can be matched to your accounts and other photos. Other people's faces are private too."],
  LICENSE_PLATE: ["car", "visual", "License plate", "A plate links a vehicle to its owner and can be used to track movements."],
  DEVICE_SCREEN: ["monitor", "visual", "Screen", "Screens often show private messages, notifications, accounts and codes that can be read in a photo."],
};

const GROUP_ORDER = {
  secret: 0, id: 1, finance: 2, contact: 3, identity: 4,
  location: 5, device: 6, work: 7, visual: 8, general: 9,
};

function humanize(type) {
  const text = String(type || "").replace(/_/g, " ").toLowerCase();
  return text.charAt(0).toUpperCase() + text.slice(1);
}

export function riskInfo(type) {
  const row = INFO[type];

  if (!row) {
    return {
      icon: "shield",
      group: "general",
      title: humanize(type) || "Sensitive information",
      why: "This looks like personal or sensitive information that could help identify you.",
    };
  }

  return { icon: row[0], group: row[1], title: row[2], why: row[3] };
}

export function TypeIcon({ type, size = 16 }) {
  const info = riskInfo(type);

  return (
    <span className={`typeIcon ${info.group}`} title={info.title}>
      <Svg name={info.icon} size={size} />
    </span>
  );
}

// Hover or focus the (i) to read why this kind of data is risky.
export function WhyTip({ type, risk }) {
  const info = riskInfo(type);

  return (
    <span className="whyTip">
      <button
        type="button"
        className="whyBtn"
        aria-label={`Why is ${info.title} risky?`}
        onClick={(event) => {
          event.preventDefault();
          event.stopPropagation();
        }}
      >
        <Svg name="info" size={15} />
      </button>

      <span className="whyPop" role="tooltip">
        <b>{info.title}</b>
        <span>{info.why}</span>
        {risk && <em>Risk level: {String(risk).toLowerCase()}</em>}
      </span>
    </span>
  );
}

export function RiskExplainer({ kinds = [] }) {
  const unique = [...new Set(kinds)].sort(
    (a, b) =>
      (GROUP_ORDER[riskInfo(a).group] ?? 9) -
      (GROUP_ORDER[riskInfo(b).group] ?? 9),
  );

  if (unique.length === 0) return null;

  return (
    <details className="explain" open>
      <summary>Why these matter</summary>

      <ul className="explainList">
        {unique.map((kind) => {
          const info = riskInfo(kind);

          return (
            <li key={kind}>
              <TypeIcon type={kind} size={18} />

              <div>
                <b>{info.title}</b>
                <p>{info.why}</p>
              </div>
            </li>
          );
        })}
      </ul>
    </details>
  );
}
