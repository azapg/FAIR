"use client";
import { useEffect } from "react";
import { useNavigate } from "react-router-dom";

export default function Page() {
  const navigate = useNavigate();
  useEffect(() => {
    navigate("/demo/courses", { replace: true });
  }, [navigate]);
  return <></>;
}

