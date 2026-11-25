SIGNATURES = [
    {
        "name": "Shopify",
        "category": "E-commerce",
        "rules": [
            ("header", "x-shopid", r".+"),
            ("cookie", "", r"^_shopify_"),
            ("script_src", "", r"^(?:https?:)?//cdn\.shopify\.com/"),
        ],
    },
    {
        "name": "WooCommerce",
        "category": "E-commerce",
        "rules": [
            ("script_src", "", r"/wp-content/plugins/woocommerce/"),
            ("selector", "body.woocommerce, body.woocommerce-page", ""),
        ],
    },
    {
        "name": "Magento",
        "category": "E-commerce",
        "rules": [
            ("cookie", "", r"^mage-cache-sessid$"),
            ("inline_script", "", r"\bMagento_[A-Z]\w*/"),
        ],
    },
    {
        "name": "PrestaShop",
        "category": "E-commerce",
        "rules": [
            ("meta", "generator", r"\bPrestaShop\b"),
            ("cookie", "", r"^PrestaShop-"),
        ],
    },
    {
        "name": "BigCommerce",
        "category": "E-commerce",
        "rules": [("script_src", "", r"^(?:https?:)?//cdn\d*\.bigcommerce\.com/")],
    },
    {
        "name": "Salesforce Commerce Cloud",
        "category": "E-commerce",
        "rules": [
            ("script_src", "", r"/on/demandware\.static/"),
            ("cookie", "", r"^dwsid$"),
        ],
    },
    {
        "name": "WordPress",
        "category": "CMS",
        "rules": [
            ("meta", "generator", r"\bWordPress\b"),
            ("script_src", "", r"/wp-(?:content|includes)/"),
            ("stylesheet", "", r"/wp-content/"),
            ("cookie", "", r"^wp-settings(?:-time)?-\d+$"),
        ],
    },
    {
        "name": "Drupal",
        "category": "CMS",
        "rules": [
            ("meta", "generator", r"\bDrupal\b"),
            ("header", "x-drupal-cache", r".+"),
            ("inline_script", "", r"\bDrupal\.settings\s*="),
        ],
    },
    {
        "name": "Joomla",
        "category": "CMS",
        "rules": [("meta", "generator", r"\bJoomla!?\b")],
    },
    {"name": "Ghost", "category": "CMS", "rules": [("meta", "generator", r"^Ghost\b")]},
    {
        "name": "Wix",
        "category": "CMS",
        "rules": [
            ("meta", "generator", r"^Wix"),
            ("script_src", "", r"^(?:https?:)?//static\.parastorage\.com/"),
        ],
    },
    {
        "name": "Squarespace",
        "category": "CMS",
        "rules": [
            (
                "script_src",
                "",
                r"^(?:https?:)?//(?:assets|static\d*)\.squarespace\.com/",
            )
        ],
    },
    {
        "name": "Webflow",
        "category": "CMS",
        "rules": [("selector", "html[data-wf-site]", "")],
    },
    {
        "name": "Google Analytics",
        "category": "Analytics/Marketing",
        "rules": [
            (
                "script_src",
                "",
                r"^(?:https?:)?//(?:www\.)?google-analytics\.com/(?:analytics|ga)\.js",
            ),
            ("inline_script", "", r"gtag\(\s*['\"]config['\"]\s*,\s*['\"](?:G-|UA-)"),
            (
                "script_src",
                "",
                r"^(?:https?:)?//www\.googletagmanager\.com/gtag/js\?[^#]*\bid=(?:G-|UA-)",
            ),
        ],
    },
    {
        "name": "Google Tag Manager",
        "category": "Analytics/Marketing",
        "rules": [
            ("script_src", "", r"^(?:https?:)?//www\.googletagmanager\.com/gtm\.js"),
            ("inline_script", "", r"googletagmanager\.com/gtm\.js"),
        ],
    },
    {
        "name": "Meta Pixel",
        "category": "Analytics/Marketing",
        "rules": [
            (
                "script_src",
                "",
                r"^(?:https?:)?//connect\.facebook\.net/[^\s]*fbevents\.js",
            ),
            ("inline_script", "", r"connect\.facebook\.net/[^'\"\s]*fbevents\.js"),
        ],
    },
    {
        "name": "Hotjar",
        "category": "Analytics/Marketing",
        "rules": [
            ("script_src", "", r"^(?:https?:)?//static\.hotjar\.com/"),
            ("inline_script", "", r"\b_hjSettings\s*="),
        ],
    },
    {
        "name": "Microsoft Clarity",
        "category": "Analytics/Marketing",
        "rules": [
            ("script_src", "", r"^(?:https?:)?//www\.clarity\.ms/tag/"),
            ("inline_script", "", r"https://www\.clarity\.ms/tag/"),
        ],
    },
    {
        "name": "Segment",
        "category": "Analytics/Marketing",
        "rules": [
            ("script_src", "", r"^(?:https?:)?//cdn\.segment\.com/"),
            ("inline_script", "", r"https://cdn\.segment\.com/analytics\.js/"),
        ],
    },
    {
        "name": "HubSpot",
        "category": "Analytics/Marketing",
        "rules": [
            ("script_src", "", r"^(?:https?:)?//js(?:-[a-z0-9]+)?\.hs-scripts\.com/")
        ],
    },
    {
        "name": "Klaviyo",
        "category": "Analytics/Marketing",
        "rules": [("script_src", "", r"^(?:https?:)?//static\.klaviyo\.com/")],
    },
    {
        "name": "Matomo",
        "category": "Analytics/Marketing",
        "rules": [("script_src", "", r"/(?:matomo|piwik)\.js(?:[?#]|$)")],
    },
    {
        "name": "React",
        "category": "JS Frameworks",
        "rules": [
            ("selector", "[data-reactroot], [data-reactid]", ""),
            (
                "script_src",
                "",
                r"/react(?:\.production\.min|\.development|\.min)?\.js(?:[?#]|$)",
            ),
        ],
    },
    {
        "name": "Next.js",
        "category": "JS Frameworks",
        "rules": [
            ("script_src", "", r"/_next/static/"),
            ("selector", "script#__NEXT_DATA__", ""),
        ],
    },
    {
        "name": "Vue.js",
        "category": "JS Frameworks",
        "rules": [
            ("selector", "[data-v-app]", ""),
            (
                "script_src",
                "",
                r"/vue(?:\.runtime)?(?:\.global)?(?:\.prod|\.min)?\.js(?:[?#]|$)",
            ),
        ],
    },
    {
        "name": "Nuxt",
        "category": "JS Frameworks",
        "rules": [
            ("script_src", "", r"/_nuxt/"),
            ("selector", "script#__NUXT_DATA__", ""),
        ],
    },
    {
        "name": "Angular",
        "category": "JS Frameworks",
        "rules": [("selector", "[ng-version]", "")],
    },
    {
        "name": "SvelteKit",
        "category": "JS Frameworks",
        "rules": [
            ("script_src", "", r"/_app/immutable/"),
            ("inline_script", "", r"\b__sveltekit_[a-z0-9]+\s*="),
        ],
    },
    {
        "name": "jQuery",
        "category": "JS Libraries",
        "rules": [
            ("script_src", "", r"/jquery(?:-\d+(?:\.\d+)*)?(?:\.min)?\.js(?:[?#]|$)")
        ],
    },
    {
        "name": "Bootstrap",
        "category": "UI Libraries",
        "rules": [
            ("stylesheet", "", r"/bootstrap(?:\.min)?\.css(?:[?#]|$)"),
            ("script_src", "", r"/bootstrap(?:\.bundle)?(?:\.min)?\.js(?:[?#]|$)"),
        ],
    },
    {
        "name": "Stripe",
        "category": "Payments",
        "rules": [("script_src", "", r"^(?:https?:)?//js\.stripe\.com/")],
    },
    {
        "name": "PayPal",
        "category": "Payments",
        "rules": [
            ("script_src", "", r"^(?:https?:)?//www\.paypal\.com/sdk/js(?:[?#]|$)")
        ],
    },
    {
        "name": "Braintree",
        "category": "Payments",
        "rules": [("script_src", "", r"^(?:https?:)?//js\.braintreegateway\.com/")],
    },
    {
        "name": "Adyen",
        "category": "Payments",
        "rules": [
            (
                "script_src",
                "",
                r"^(?:https?:)?//checkoutshopper-(?:live|test)\.adyen\.com/",
            )
        ],
    },
    {
        "name": "Cloudflare",
        "category": "Hosting/CDN",
        "rules": [("header", "cf-ray", r".+"), ("header", "server", r"^cloudflare$")],
    },
    {
        "name": "Amazon CloudFront",
        "category": "Hosting/CDN",
        "rules": [
            ("header", "x-amz-cf-id", r".+"),
            ("header", "via", r"\bCloudFront\b"),
        ],
    },
    {
        "name": "Fastly",
        "category": "Hosting/CDN",
        "rules": [
            ("header", "x-served-by", r"\bcache-[a-z]+\d+-[a-z]+\b"),
            ("header", "fastly-restarts", r"^\d+$"),
        ],
    },
    {
        "name": "Vercel",
        "category": "Hosting/CDN",
        "rules": [("header", "x-vercel-id", r".+")],
    },
    {
        "name": "Netlify",
        "category": "Hosting/CDN",
        "rules": [("header", "x-nf-request-id", r".+")],
    },
    {
        "name": "nginx",
        "category": "Backend",
        "rules": [("header", "server", r"^nginx\b")],
    },
    {
        "name": "Apache HTTP Server",
        "category": "Backend",
        "rules": [("header", "server", r"^Apache\b")],
    },
    {
        "name": "Microsoft IIS",
        "category": "Backend",
        "rules": [("header", "server", r"^Microsoft-IIS\b")],
    },
    {
        "name": "LiteSpeed",
        "category": "Backend",
        "rules": [("header", "server", r"^LiteSpeed\b")],
    },
    {
        "name": "PHP",
        "category": "Backend",
        "rules": [
            ("header", "x-powered-by", r"\bPHP\b"),
            ("cookie", "", r"^PHPSESSID$"),
        ],
    },
    {
        "name": "ASP.NET",
        "category": "Backend",
        "rules": [
            ("header", "x-powered-by", r"\bASP\.NET\b"),
            ("header", "x-aspnet-version", r".+"),
            ("cookie", "", r"^ASP\.NET_SessionId$"),
        ],
    },
    {
        "name": "Express",
        "category": "Backend",
        "rules": [("header", "x-powered-by", r"^Express$")],
    },
    {
        "name": "Laravel",
        "category": "Backend",
        "rules": [("cookie", "", r"^laravel_session$")],
    },
]
