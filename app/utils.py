import matplotlib

matplotlib.use("Agg")  # GUI 없이 이미지로 저장 가능하게 설정

import datetime
import os
import uuid

import matplotlib.pyplot as plt


def generate_chart_image(code: str, output_dir: str) -> str:
    # Set unique filename
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    uuid_str = str(uuid.uuid4())[:8]  # Generate a unique user ID
    filename = f"{timestamp}_{uuid_str}.png"
    filepath = os.path.join(output_dir, filename)

    # Define a local namespace for exec
    local_ns = {"plt": plt}

    try:
        exec(code, {}, local_ns)  # code must create a plot using plt
        plt.savefig(filepath)
        plt.close()
        return filename
    except Exception as e:
        plt.close()
        raise RuntimeError(f"Chart generation failed: {str(e)}")
