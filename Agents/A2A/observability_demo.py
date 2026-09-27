import asyncio
import os
import time

from dotenv import load_dotenv

# ---------------------------------------------------------
# IMPORTANT:
# Set observability environment variables BEFORE importing
# Agent Framework.
# ---------------------------------------------------------

os.environ["ENABLE_INSTRUMENTATION"] = "true"
os.environ["ENABLE_SENSITIVE_DATA"] = "false"

from azure.identity.aio import AzureCliCredential

from agent_framework.foundry import FoundryChatClient
from agent_framework.observability import enable_instrumentation

from opentelemetry import trace
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, SpanExporter, SpanExportResult


# =========================================================
# CUSTOM SPAN COLLECTOR
#
# Instead of dumping raw OpenTelemetry JSON to the console,
# this collector keeps completed spans in memory so that
# we can print them nicely at the end.
# =========================================================

class LocalSpanCollector(SpanExporter):

    def __init__(self):
        self.spans = []

    def export(self, spans):
        self.spans.extend(spans)
        return SpanExportResult.SUCCESS

    def shutdown(self):
        pass


def get_attribute(attributes, *names):
    """
    Return the first matching OpenTelemetry attribute.
    Different SDK/model versions can expose slightly
    different attribute names.
    """

    for name in names:
        if name in attributes:
            return attributes[name]

    return None


def milliseconds(span: ReadableSpan):
    if span.start_time is None or span.end_time is None:
        return None

    return (span.end_time - span.start_time) / 1_000_000


def print_value(label, value, indent="   "):
    if value is not None:
        print(f"{indent}{label:<22}: {value}")


def print_observability_summary(
    spans,
    total_latency,
    application_success,
    application_error,
):
    print()
    print("============================================================")
    print("OBSERVABILITY SUMMARY")
    print("============================================================")

    if not spans:
        print()
        print("No Agent Framework spans were captured.")
        return

    # -----------------------------------------------------
    # TRACE
    # -----------------------------------------------------

    first_span = spans[0]

    trace_id = format(
        first_span.context.trace_id,
        "032x",
    )

    print()
    print("TRACE")
    print("------------------------------------------------------------")
    print_value("Trace ID", trace_id)
    print_value("Captured spans", len(spans))

    print()
    print("SPAN TREE")
    print("------------------------------------------------------------")

    for span in spans:

        span_id = format(
            span.context.span_id,
            "016x",
        )

        parent_span_id = None

        if span.parent is not None:
            parent_span_id = format(
                span.parent.span_id,
                "016x",
            )

        duration = milliseconds(span)

        print()
        print(f"   {span.name}")

        print_value(
            "Span ID",
            span_id,
            indent="      ",
        )

        print_value(
            "Parent Span ID",
            parent_span_id,
            indent="      ",
        )

        if duration is not None:
            print_value(
                "Duration",
                f"{duration:.2f} ms",
                indent="      ",
            )

        print_value(
            "Status",
            span.status.status_code.name,
            indent="      ",
        )

    # -----------------------------------------------------
    # AGENT
    # -----------------------------------------------------

    print()
    print("AGENT")
    print("------------------------------------------------------------")

    agent_found = False

    for span in spans:

        attributes = dict(span.attributes)

        agent_name = get_attribute(
            attributes,
            "gen_ai.agent.name",
        )

        agent_id = get_attribute(
            attributes,
            "gen_ai.agent.id",
        )

        operation = get_attribute(
            attributes,
            "gen_ai.operation.name",
        )

        if agent_name is not None or operation == "invoke_agent":

            agent_found = True

            print_value(
                "Agent name",
                agent_name or "SupportAgent",
            )

            print_value(
                "Agent ID",
                agent_id,
            )

            duration = milliseconds(span)

            if duration is not None:
                print_value(
                    "Execution duration",
                    f"{duration:.2f} ms",
                )

            print_value(
                "Success",
                span.status.status_code.name != "ERROR",
            )

            break

    if not agent_found:
        print("   No agent-specific span attributes found.")

    # -----------------------------------------------------
    # MODEL
    # -----------------------------------------------------

    print()
    print("MODEL")
    print("------------------------------------------------------------")

    total_input_tokens = 0
    total_output_tokens = 0

    model_calls = 0

    for span in spans:

        attributes = dict(span.attributes)

        input_tokens = get_attribute(
            attributes,
            "gen_ai.usage.input_tokens",
            "gen_ai.usage.prompt_tokens",
        )

        output_tokens = get_attribute(
            attributes,
            "gen_ai.usage.output_tokens",
            "gen_ai.usage.completion_tokens",
        )

        model = get_attribute(
            attributes,
            "gen_ai.response.model",
            "gen_ai.request.model",
        )

        provider = get_attribute(
            attributes,
            "gen_ai.provider.name",
            "gen_ai.system",
        )

        response_id = get_attribute(
            attributes,
            "gen_ai.response.id",
        )

        operation = get_attribute(
            attributes,
            "gen_ai.operation.name",
        )

        if (
            input_tokens is not None
            or output_tokens is not None
            or model is not None
            or operation == "chat"
        ):
            model_calls += 1

            print()
            print(f"   Model call #{model_calls}")

            print_value(
                "Model",
                model,
                indent="      ",
            )

            print_value(
                "Provider",
                provider,
                indent="      ",
            )

            print_value(
                "Response ID",
                response_id,
                indent="      ",
            )

            print_value(
                "Input tokens",
                input_tokens,
                indent="      ",
            )

            print_value(
                "Output tokens",
                output_tokens,
                indent="      ",
            )

            duration = milliseconds(span)

            if duration is not None:
                print_value(
                    "Duration",
                    f"{duration:.2f} ms",
                    indent="      ",
                )

            if input_tokens is not None:
                total_input_tokens += int(input_tokens)

            if output_tokens is not None:
                total_output_tokens += int(output_tokens)

    if model_calls == 0:
        print("   No model-call telemetry found.")

    print()
    print("   TOTAL MODEL USAGE")
    print_value(
        "Model calls",
        model_calls,
        indent="      ",
    )

    print_value(
        "Input tokens",
        total_input_tokens,
        indent="      ",
    )

    print_value(
        "Output tokens",
        total_output_tokens,
        indent="      ",
    )

    print_value(
        "Total tokens",
        total_input_tokens + total_output_tokens,
        indent="      ",
    )

    # -----------------------------------------------------
    # TOOLS
    # -----------------------------------------------------

    print()
    print("TOOLS")
    print("------------------------------------------------------------")

    tool_calls = 0

    for span in spans:

        attributes = dict(span.attributes)

        operation = get_attribute(
            attributes,
            "gen_ai.operation.name",
        )

        tool_name = get_attribute(
            attributes,
            "gen_ai.tool.name",
            "gen_ai.tool.call.name",
            "tool.name",
        )

        if operation == "execute_tool" or tool_name is not None:

            tool_calls += 1

            print()
            print(f"   Tool call #{tool_calls}")

            print_value(
                "Tool name",
                tool_name or span.name,
                indent="      ",
            )

            duration = milliseconds(span)

            if duration is not None:
                print_value(
                    "Duration",
                    f"{duration:.2f} ms",
                    indent="      ",
                )

            print_value(
                "Success",
                span.status.status_code.name != "ERROR",
                indent="      ",
            )

    if tool_calls == 0:
        print("   Tool calls              : 0")
        print("   This demo agent has no tools.")

    # -----------------------------------------------------
    # ERRORS
    # -----------------------------------------------------

    print()
    print("ERRORS")
    print("------------------------------------------------------------")

    error_spans = [
        span
        for span in spans
        if span.status.status_code.name == "ERROR"
    ]

    print_value(
        "Error spans",
        len(error_spans),
    )

    if application_error is not None:
        print_value(
            "Application error",
            application_error,
        )

    # -----------------------------------------------------
    # APPLICATION
    # -----------------------------------------------------

    print()
    print("APPLICATION")
    print("------------------------------------------------------------")

    print_value(
        "End-to-end latency",
        f"{total_latency:.2f} seconds",
    )

    print_value(
        "Success",
        application_success,
    )

    print_value(
        "Failures",
        0 if application_success else 1,
    )

    print()
    print("============================================================")


async def main():

    load_dotenv()

    project_endpoint = os.getenv("PROJECT_ENDPOINT")
    model_deployment_name = os.getenv("MODEL_DEPLOYMENT_NAME")

    if not project_endpoint:
        raise ValueError(
            "PROJECT_ENDPOINT is not set in .env"
        )

    if not model_deployment_name:
        raise ValueError(
            "MODEL_DEPLOYMENT_NAME is not set in .env"
        )

    # ---------------------------------------------------------
    # Enable Agent Framework instrumentation.
    #
    # Azure Monitor will configure the global OpenTelemetry
    # providers. We then attach our collector to the same
    # tracer provider.
    # ---------------------------------------------------------

    enable_instrumentation(
        enable_sensitive_data=False
    )

    collector = LocalSpanCollector()

    async with AzureCliCredential() as credential:

        chat_client = FoundryChatClient(
            project_endpoint=project_endpoint,
            model=model_deployment_name,
            credential=credential,
        )

        # -----------------------------------------------------
        # Azure Monitor / Application Insights exporter
        # -----------------------------------------------------

        await chat_client.configure_azure_monitor(
            enable_live_metrics=True
        )

        # -----------------------------------------------------
        # Attach our local span collector to the SAME provider.
        # -----------------------------------------------------

        tracer_provider = trace.get_tracer_provider()

        if not hasattr(
            tracer_provider,
            "add_span_processor",
        ):
            raise RuntimeError(
                "The current OpenTelemetry tracer provider "
                "does not support span processors."
            )

        tracer_provider.add_span_processor(
            SimpleSpanProcessor(collector)
        )

        # -----------------------------------------------------
        # Create agent
        # -----------------------------------------------------

        support_agent = chat_client.as_agent(
            name="SupportAgent",
            instructions=(
                "You are a company IT support agent. "
                "Answer questions clearly and concisely."
            ),
        )

        question = (
            "Explain in one short sentence why employees "
            "working remotely should use a VPN."
        )

        print()
        print("============================================================")
        print("USER QUESTION")
        print("============================================================")
        print(question)

        start_time = time.perf_counter()

        success = False
        application_error = None
        response = None

        try:

            response = await support_agent.run(
                question
            )

            success = True

        except Exception as exc:

            application_error = str(exc)

        total_latency = (
            time.perf_counter() - start_time
        )

        print()
        print("============================================================")
        print("AGENT RESPONSE")
        print("============================================================")

        if response is not None:
            print(response.text)
        else:
            print("No response")

        # -----------------------------------------------------
        # Allow completed telemetry to reach our processor.
        # -----------------------------------------------------

        await asyncio.sleep(1)

        # -----------------------------------------------------
        # Print readable observability report
        # -----------------------------------------------------

        print_observability_summary(
            spans=collector.spans,
            total_latency=total_latency,
            application_success=success,
            application_error=application_error,
        )


if __name__ == "__main__":
    asyncio.run(main())