import { useEffect } from "react";
import { useNavigate } from "react-router-dom";

//TODO: in the future, there should be a landing page for docs and info about the project
export default function Page() {
  const navigate = useNavigate();
  useEffect(() => {
    navigate("/demo/courses", { replace: true });
  }, [navigate]);
  return <></>;
}

