import { ExternalLink, KeyRound, ShieldAlert, BookOpen } from "lucide-react";
import { Link } from "react-router-dom";
import { panel, btnPrimary, link } from "../components/styles";

export default function HelpOpenRouterFree() {
  return (
    <div className="max-w-4xl mx-auto space-y-6" data-testid="help-openrouter-page">
      <div className={panel}>
        <div className="flex items-center gap-2 mb-4 border-b-2 border-gray-300 pb-3">
          <BookOpen size={24} className="text-blue-700" />
          <h1 className="text-xl font-black text-black uppercase tracking-wide">
            Guide: Free OpenRouter API Key Setup
          </h1>
        </div>

        <p className="text-sm font-bold text-gray-900 mb-6 leading-relaxed">
          OpenRouter provides access to a variety of large language models with a single unified API key,
          including free community model variants with zero credit purchase required. Follow this guide to create a free key
          and use it in Tender Integrity Suite.
        </p>

        {/* 3 Steps */}
        <div className="space-y-4 mb-8">
          <div className="p-4 bg-gray-50 border-2 border-gray-900 rounded-lg">
            <h2 className="text-sm font-black uppercase tracking-wider text-gray-950 mb-1">
              Step 1: Create an OpenRouter Account
            </h2>
            <p className="text-sm font-semibold text-gray-800">
              Go to{" "}
              <a
                href="https://openrouter.ai"
                target="_blank"
                rel="noreferrer"
                className={`inline-flex items-center gap-1 ${link}`}
              >
                openrouter.ai <ExternalLink size={13} />
              </a>{" "}
              and sign up with Google, GitHub, or your email. No credit card is required to access free tier models.
            </p>
          </div>

          <div className="p-4 bg-gray-50 border-2 border-gray-900 rounded-lg">
            <h2 className="text-sm font-black uppercase tracking-wider text-gray-950 mb-1">
              Step 2: Generate an API Key
            </h2>
            <p className="text-sm font-semibold text-gray-800">
              Navigate to{" "}
              <a
                href="https://openrouter.ai/keys"
                target="_blank"
                rel="noreferrer"
                className={`inline-flex items-center gap-1 ${link}`}
              >
                openrouter.ai/keys <ExternalLink size={13} />
              </a>
              , click <strong>Create Key</strong>, give it a name (e.g., <em>TenderFender</em>), and copy the key (starting with <code>{"sk-" + "or-v1-..."}</code>).
            </p>
          </div>

          <div className="p-4 bg-gray-50 border-2 border-gray-900 rounded-lg">
            <h2 className="text-sm font-black uppercase tracking-wider text-gray-950 mb-1">
              Step 3: Paste Key into TenderFender
            </h2>
            <p className="text-sm font-semibold text-gray-800 mb-3">
              Go to TenderFender's AI Settings page, paste your key into the input field, and click <strong>Detect key</strong>.
              Your free models will be automatically recognized.
            </p>
            <Link to="/settings/ai" className={btnPrimary}>
              <KeyRound size={15} /> Go to AI Settings
            </Link>
          </div>
        </div>

        {/* Verbatim Docs Quotes: Rate Limits */}
        <div className="border-t-4 border-gray-900 pt-6 space-y-6">
          <div>
            <h2 className="text-lg font-black text-black uppercase tracking-wide mb-2">
              Official OpenRouter Free Tier Limits
            </h2>
            <p className="text-xs font-semibold text-gray-700 mb-3">
              Source: Official OpenRouter documentation at{" "}
              <a
                href="https://openrouter.ai/docs/api_reference/limits"
                target="_blank"
                rel="noreferrer"
                className={link}
              >
                openrouter.ai/docs/api_reference/limits <ExternalLink size={12} className="inline" />
              </a>
              . Quoted verbatim:
            </p>

            <blockquote className="p-4 bg-amber-50 border-l-4 border-amber-600 rounded text-xs font-mono text-gray-950 space-y-2">
              <p className="font-bold">
                "Rate limits govern how many requests you can make. There are a few rate limits that apply to certain types of requests, regardless of account status:
              </p>
              <p className="font-bold">
                1. Free usage limits: If you're using a free model variant (with an ID ending in :free), the following limits apply:
              </p>
              <div className="overflow-x-auto my-2">
                <table className="border-collapse border border-gray-700 text-xs w-full">
                  <thead>
                    <tr className="bg-amber-200 text-left">
                      <th className="border border-gray-700 p-1.5 font-black">Credits purchased (all time)</th>
                      <th className="border border-gray-700 p-1.5 font-black">Requests per minute</th>
                      <th className="border border-gray-700 p-1.5 font-black">Requests per day</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td className="border border-gray-700 p-1.5 font-semibold">Less than 10</td>
                      <td className="border border-gray-700 p-1.5 font-semibold">20</td>
                      <td className="border border-gray-700 p-1.5 font-semibold">50</td>
                    </tr>
                    <tr>
                      <td className="border border-gray-700 p-1.5 font-semibold">At least 10</td>
                      <td className="border border-gray-700 p-1.5 font-semibold">20</td>
                      <td className="border border-gray-700 p-1.5 font-semibold">1000</td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <p className="font-bold">
                The free_model_daily_requests field in the GET /api/v1/key response above reports the daily counter and ceiling that gate your free-model requests when these limits apply to your account."
              </p>
            </blockquote>
          </div>

          {/* Model Variants */}
          <div>
            <h2 className="text-sm font-black uppercase tracking-wider text-black mb-1">
              Model Variants & Free Router
            </h2>
            <p className="text-xs font-semibold text-gray-700 mb-2">
              Sources:{" "}
              <a
                href="https://openrouter.ai/docs/guides/routing/model-variants/free"
                target="_blank"
                rel="noreferrer"
                className={link}
              >
                Model Variants / Free <ExternalLink size={12} className="inline" />
              </a>{" "}
              and{" "}
              <a
                href="https://openrouter.ai/docs/guides/routing/routers/free-router"
                target="_blank"
                rel="noreferrer"
                className={link}
              >
                Free Models Router <ExternalLink size={12} className="inline" />
              </a>
              :
            </p>
            <blockquote className="p-4 bg-gray-100 border-l-4 border-gray-700 rounded text-xs font-mono text-gray-900 space-y-2">
              <p>
                "The :free variant allows you to access free versions of models on OpenRouter. Append :free to the ID of a model that has a free entry. :free is a catalog variant, so the free version appears as its own entry in the models API with its own pricing, context length, and endpoints, and only models that list one support it."
              </p>
              <p>
                "The Free Models Router (openrouter/free) automatically selects a free model at random from the available free models on OpenRouter. The router intelligently filters for models that support the features your request needs..."
              </p>
            </blockquote>
          </div>

          {/* Provider Logging & Privacy */}
          <div>
            <h2 className="text-sm font-black uppercase tracking-wider text-black mb-1">
              Provider Logging & Privacy Policies
            </h2>
            <p className="text-xs font-semibold text-gray-700 mb-2">
              Source:{" "}
              <a
                href="https://openrouter.ai/docs/guides/privacy/provider-logging"
                target="_blank"
                rel="noreferrer"
                className={link}
              >
                OpenRouter Provider Logging <ExternalLink size={12} className="inline" />
              </a>
              :
            </p>
            <blockquote className="p-4 bg-gray-100 border-l-4 border-gray-700 rounded text-xs font-mono text-gray-900 space-y-2">
              <p>
                "Each provider on OpenRouter has its own data handling policies. We reflect those policies in structured data on each AI endpoint that we offer. On your account settings page, you can set whether you would like to allow routing to providers that may train on your data (according to their own policies). There are separate settings for paid and free models."
              </p>
              <p>
                "Wherever possible, OpenRouter works with providers to ensure that prompts will not be trained on, but there are exceptions."
              </p>
            </blockquote>
          </div>

          {/* Expectations and Limitations */}
          <div className="p-4 bg-blue-50 border-2 border-blue-600 rounded-lg space-y-2">
            <h3 className="text-sm font-black uppercase tracking-wider text-blue-950 flex items-center gap-1.5">
              <ShieldAlert size={18} className="text-blue-700" /> What to Expect on Free Models
            </h3>
            <ul className="list-disc pl-5 text-xs font-bold text-blue-950 space-y-1">
              <li>
                <strong>Latency & Queuing:</strong> Free models can take 30 to 90 seconds to respond, especially during peak internet traffic periods.
              </li>
              <li>
                <strong>Occasional Failures:</strong> Upstream free providers may return HTTP 429 or 503 when overloaded. TenderFender displays clear provider error messages when this occurs.
              </li>
              <li>
                <strong>Data Handling:</strong> Upstream free providers may log or train on prompts according to their published terms. <em>Always use synthetic, public, or sample tender data</em>. Never paste confidential bids, secret pricing models, or internal procurement memos.
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
