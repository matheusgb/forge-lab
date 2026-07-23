def greeting(name: str) -> str:
    """Cria a saída observável mais simples do laboratório."""
    normalized_name = name.strip()
    if not normalized_name:
        raise ValueError("name cannot be empty")
    return f"Ambiente pronto, {normalized_name}!"
